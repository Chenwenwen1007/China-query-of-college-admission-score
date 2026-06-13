from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from openpyxl import Workbook

from province_config import (
    DEFAULT_PROVINCE_SLUG,
    build_scope_summary,
    build_year_range_text,
    list_province_slugs,
    load_province_config,
)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
HOST = "127.0.0.1"
PORT = 8000

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

ACTIVE_PROVINCE_SLUG = DEFAULT_PROVINCE_SLUG
PROVINCE_CONFIG = load_province_config(ACTIVE_PROVINCE_SLUG)
DB_PATH = BASE_DIR / PROVINCE_CONFIG["database_filename"]
RUNTIME_CACHE: dict[str, dict[str, Any]] = {}


def configure_runtime(province_slug: str) -> None:
    global ACTIVE_PROVINCE_SLUG, PROVINCE_CONFIG, DB_PATH

    ACTIVE_PROVINCE_SLUG = province_slug
    PROVINCE_CONFIG = load_province_config(province_slug)
    DB_PATH = BASE_DIR / PROVINCE_CONFIG["database_filename"]
    RUNTIME_CACHE[province_slug] = {
        "province_slug": province_slug,
        "config": PROVINCE_CONFIG,
        "db_path": DB_PATH,
    }


def get_runtime_context(province_slug: str | None = None) -> dict[str, Any]:
    slug = (province_slug or ACTIVE_PROVINCE_SLUG).strip() or ACTIVE_PROVINCE_SLUG
    cached = RUNTIME_CACHE.get(slug)
    if cached is not None:
        return cached

    config = load_province_config(slug)
    db_path = BASE_DIR / config["database_filename"]
    context = {
        "province_slug": slug,
        "config": config,
        "db_path": db_path,
    }
    RUNTIME_CACHE[slug] = context
    return context


def list_available_provinces() -> list[dict[str, Any]]:
    provinces: list[dict[str, Any]] = []
    for slug in list_province_slugs():
        context = get_runtime_context(slug)
        config = context["config"]
        provinces.append(
            {
                "slug": slug,
                "name": config.get("province_name", slug),
                "year_range": build_year_range_text(config),
                "score_min": config.get("score_range", {}).get("min"),
                "score_max": config.get("score_range", {}).get("max"),
                "subject_label": " / ".join(config.get("user_subjects", [])),
                "database_ready": context["db_path"].exists(),
            }
        )
    return provinces


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database_ready(province_slug: str | None = None) -> dict[str, Any]:
    context = get_runtime_context(province_slug)
    if not context["db_path"].exists():
        raise FileNotFoundError(
            f"database not found for province '{context['province_slug']}': {context['db_path']}"
        )
    return context


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def classify_tier(user_score: int, line_score: int) -> tuple[str, int]:
    delta = user_score - line_score
    if line_score > user_score + 10:
        return "未达", delta
    if line_score >= user_score - 3:
        return "冲", delta
    if line_score >= user_score - 12:
        return "稳", delta
    return "保", delta


def tier_description(tier: str) -> str:
    return {
        "冲": "历史线落在你的分数下 3 分到上 10 分之间",
        "稳": "历史线比你的分数低 4-12 分",
        "保": "历史线比你的分数低 13 分及以上",
        "未达": "历史线高出你的分数 11 分及以上",
    }.get(tier, "")


def clean_major_key(major_code: str | None, major_name: str | None) -> str:
    code = (major_code or "").strip()
    name = (major_name or "").strip()
    return code if code else f"name::{name}"


def build_current_source_links(config: dict[str, Any]) -> list[dict[str, Any]]:
    current_sources: list[dict[str, Any]] = []
    for year_text, source in sorted(config.get("official_sources", {}).items(), key=lambda item: int(item[0]), reverse=True):
        current_sources.append(
            {
                "year": int(year_text),
                "title": source.get("title", ""),
                "publisher": source.get("publisher", ""),
                "landing_url": source.get("landing_url", ""),
                "file_url": source.get("file_url", ""),
                "source_format": source.get("source_format", ""),
            }
        )
    return current_sources


def build_legacy_year_notes(config: dict[str, Any]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for note in config.get("legacy_year_notes", []):
        notes.append(
            {
                "year": note.get("year"),
                "title": note.get("title", ""),
                "summary": note.get("summary", ""),
                "sources": note.get("sources", []),
            }
        )
    return notes


def fetch_meta(province_slug: str | None = None) -> dict[str, Any]:
    context = ensure_database_ready(province_slug)
    config = context["config"]
    with get_connection(context["db_path"]) as conn:
        bounds = conn.execute(
            """
            SELECT
                MIN(score) AS min_score,
                MAX(score) AS max_score,
                COUNT(*) AS major_rows,
                COUNT(DISTINCT school_name) AS school_count
            FROM eligible_majors
            """
        ).fetchone()
        years = [
            row["year"]
            for row in conn.execute(
                """
                SELECT DISTINCT year
                FROM eligible_majors
                ORDER BY year DESC
                """
            ).fetchall()
        ]
        legacy_school_line_count = 0
        legacy_school_line_years: list[int] = []
        if table_exists(conn, "legacy_school_lines"):
            legacy_bounds = conn.execute(
                """
                SELECT COUNT(*) AS line_count
                FROM legacy_school_lines
                """
            ).fetchone()
            legacy_school_line_count = legacy_bounds["line_count"] if legacy_bounds else 0
            legacy_school_line_years = [
                row["year"]
                for row in conn.execute(
                    """
                    SELECT DISTINCT year
                    FROM legacy_school_lines
                    ORDER BY year DESC
                    """
                ).fetchall()
            ]

    subject_label = " / ".join(config.get("user_subjects", []))
    score_range = config.get("score_range", {})
    province_name = config.get("province_name", context["province_slug"])
    return {
        "province_slug": context["province_slug"],
        "province_name": province_name,
        "subject_label": subject_label,
        "configured_score_min": score_range.get("min"),
        "configured_score_max": score_range.get("max"),
        "configured_year_range": build_year_range_text(config),
        "scope_summary": build_scope_summary(config),
        "score_min": bounds["min_score"],
        "score_max": bounds["max_score"],
        "major_rows": bounds["major_rows"],
        "school_count": bounds["school_count"],
        "years": years,
        "legacy_school_line_count": legacy_school_line_count,
        "legacy_school_line_years": legacy_school_line_years,
        "legacy_view_note": config.get("legacy_view_note", "").strip(),
        "search_data_note": config.get(
            "search_data_note",
            f"当前检索直接使用 {province_name}{build_year_range_text(config)} 年已入库的可报专业组数据。",
        ),
        "current_sources": build_current_source_links(config),
        "legacy_year_notes": build_legacy_year_notes(config),
        "available_provinces": list_available_provinces(),
        "app_title": f"{province_name}{subject_label.replace(' / ', '')}志愿检索台",
        "app_eyebrow": f"{province_name} Admissions Planner",
        "hero_kicker": "真实数据，本地检索",
        "hero_title": "输入你的分数，直接看可考虑的学校、专业组和专业明细",
        "hero_text": (
            f"数据来自本地 SQLite，检索口径为{province_name}考生、{subject_label}、"
            f"{build_year_range_text(config)} 年。页面支持冲稳保分层、学校收藏，以及当前结果导出为 Excel / CSV。"
        ),
        "tier_rules": {
            "冲": tier_description("冲"),
            "稳": tier_description("稳"),
            "保": tier_description("保"),
        },
    }


def fetch_school_detail(school_name: str, user_score: int, province_slug: str | None = None) -> dict[str, Any]:
    context = ensure_database_ready(province_slug)
    with get_connection(context["db_path"]) as conn:
        rows = conn.execute(
            """
            SELECT
                em.year,
                em.school_code,
                COALESCE(NULLIF(sm.gaokao_school_name, ''), em.school_name) AS display_school_name,
                em.official_group_code,
                em.official_group_name,
                em.official_group_category,
                em.score,
                em.elective_info,
                COUNT(*) AS major_count,
                MIN(em.tuition) AS tuition_min,
                MAX(em.tuition) AS tuition_max
            FROM eligible_majors em
            LEFT JOIN school_mappings sm
                ON sm.school_name_official = em.school_name
            WHERE COALESCE(NULLIF(sm.gaokao_school_name, ''), em.school_name) = ?
            GROUP BY
                em.year,
                em.school_code,
                display_school_name,
                em.official_group_code,
                em.official_group_name,
                em.official_group_category,
                em.score,
                em.elective_info
            ORDER BY em.year ASC, em.score DESC, em.official_group_code ASC
            """,
            (school_name,),
        ).fetchall()
        legacy_rows: list[sqlite3.Row] = []
        if table_exists(conn, "legacy_school_lines"):
            legacy_rows = conn.execute(
                """
                SELECT
                    lsl.year,
                    lsl.batch,
                    lsl.subject_type,
                    lsl.school_code,
                    COALESCE(NULLIF(sm.gaokao_school_name, ''), lsl.school_name) AS display_school_name,
                    lsl.school_name AS school_name_official,
                    lsl.score,
                    lsl.rank_value,
                    lsl.note,
                    lsl.source_url
                FROM legacy_school_lines lsl
                LEFT JOIN school_mappings sm
                    ON sm.school_name_official = lsl.school_name
                WHERE COALESCE(NULLIF(sm.gaokao_school_name, ''), lsl.school_name) = ?
                ORDER BY lsl.year ASC, lsl.score DESC, lsl.batch ASC
                """,
                (school_name,),
            ).fetchall()

    if not rows:
        if not legacy_rows:
            raise KeyError(f"school not found: {school_name}")

    years: dict[int, dict[str, Any]] = {}
    for row in rows:
        tier, delta = classify_tier(user_score, row["score"])
        year_bucket = years.setdefault(
            row["year"],
            {
                "year": row["year"],
                "min_score": row["score"],
                "max_score": row["score"],
                "score_sum": 0,
                "group_count": 0,
                "major_count": 0,
                "groups": [],
            },
        )
        year_bucket["min_score"] = min(year_bucket["min_score"], row["score"])
        year_bucket["max_score"] = max(year_bucket["max_score"], row["score"])
        year_bucket["score_sum"] += row["score"]
        year_bucket["group_count"] += 1
        year_bucket["major_count"] += row["major_count"]
        year_bucket["groups"].append(
            {
                "official_group_code": row["official_group_code"],
                "official_group_name": row["official_group_name"],
                "official_group_category": row["official_group_category"],
                "score": row["score"],
                "score_delta": delta,
                "recommendation_tier": tier,
                "elective_info": row["elective_info"],
                "major_count": row["major_count"],
                "tuition_min": row["tuition_min"],
                "tuition_max": row["tuition_max"],
            }
        )

    yearly: list[dict[str, Any]] = []
    for year in sorted(years):
        bucket = years[year]
        bucket["avg_score"] = round(bucket["score_sum"] / bucket["group_count"], 1)
        bucket.pop("score_sum", None)
        yearly.append(bucket)

    legacy_yearly: list[dict[str, Any]] = []
    legacy_by_year: dict[int, dict[str, Any]] = {}
    for row in legacy_rows:
        tier, delta = classify_tier(user_score, row["score"])
        bucket = legacy_by_year.setdefault(
            row["year"],
            {
                "year": row["year"],
                "min_score": row["score"],
                "max_score": row["score"],
                "school_count": 0,
                "lines": [],
            },
        )
        bucket["min_score"] = min(bucket["min_score"], row["score"])
        bucket["max_score"] = max(bucket["max_score"], row["score"])
        bucket["school_count"] += 1
        bucket["lines"].append(
            {
                "batch": row["batch"],
                "subject_type": row["subject_type"],
                "score": row["score"],
                "score_delta": delta,
                "recommendation_tier": tier,
                "rank_value": row["rank_value"],
                "note": row["note"],
                "source_url": row["source_url"],
            }
        )
    for year in sorted(legacy_by_year):
        legacy_yearly.append(legacy_by_year[year])

    province_name = context["config"].get("province_name", context["province_slug"])
    note = f"趋势基于当前数据库中已入库的 {province_name} 可报专业组数据。"
    detail_scope_note = context["config"].get("detail_scope_note", "").strip()
    if detail_scope_note:
        note = f"{note} {detail_scope_note}"
    return {
        "province_slug": context["province_slug"],
        "province_name": province_name,
        "school_name": rows[0]["display_school_name"] if rows else legacy_rows[0]["display_school_name"],
        "school_code": rows[0]["school_code"] if rows else legacy_rows[0]["school_code"],
        "user_score": user_score,
        "yearly": yearly,
        "legacy_school_lines": legacy_yearly,
        "legacy_school_line_note": context["config"].get("legacy_view_note", "").strip(),
        "note": note,
    }


def fetch_legacy_school_lines(
    province_slug: str,
    score: int,
    min_score: int | None,
    school_keyword: str,
    limit: int,
) -> dict[str, Any]:
    context = ensure_database_ready(province_slug)
    score_where_parts = ["lsl.score <= :max_score"]
    if min_score is not None:
        score_where_parts.append("lsl.score >= :min_score")
    if school_keyword:
        score_where_parts.append(
            "(lsl.school_name LIKE :school_keyword_like OR COALESCE(NULLIF(sm.gaokao_school_name, ''), lsl.school_name) LIKE :school_keyword_like)"
        )
    where_clause = " AND ".join(score_where_parts)
    params = {
        "score": score,
        "max_score": score + 10,
        "min_score": min_score,
        "school_keyword_like": f"%{school_keyword}%",
        "limit": limit,
    }

    with get_connection(context["db_path"]) as conn:
        if not table_exists(conn, "legacy_school_lines"):
            return {
                "note": context["config"].get("legacy_view_note", "").strip(),
                "summary": {"row_count": 0, "school_count": 0, "returned_count": 0},
                "items": [],
            }
        rows = conn.execute(
            f"""
            SELECT
                lsl.year,
                lsl.batch,
                lsl.subject_type,
                lsl.school_code,
                COALESCE(NULLIF(sm.gaokao_school_name, ''), lsl.school_name) AS school_name,
                lsl.score,
                lsl.rank_value,
                lsl.note,
                lsl.source_url
            FROM legacy_school_lines lsl
            LEFT JOIN school_mappings sm
                ON sm.school_name_official = lsl.school_name
            WHERE {where_clause}
            ORDER BY lsl.score DESC, lsl.year DESC, school_name ASC, lsl.batch ASC
            LIMIT :limit
            """,
            params,
        ).fetchall()

        total = conn.execute(
            f"""
            SELECT COUNT(*) AS row_count, COUNT(DISTINCT COALESCE(NULLIF(sm.gaokao_school_name, ''), lsl.school_name)) AS school_count
            FROM legacy_school_lines lsl
            LEFT JOIN school_mappings sm
                ON sm.school_name_official = lsl.school_name
            WHERE {where_clause}
            """,
            {key: value for key, value in params.items() if key != "limit"},
        ).fetchone()

    items: list[dict[str, Any]] = []
    for row in rows:
        tier, delta = classify_tier(score, row["score"])
        items.append(
            {
                "year": row["year"],
                "batch": row["batch"],
                "subject_type": row["subject_type"],
                "school_code": row["school_code"],
                "school_name": row["school_name"],
                "score": row["score"],
                "score_delta": delta,
                "recommendation_tier": tier,
                "recommendation_hint": tier_description(tier),
                "rank_value": row["rank_value"],
                "note": row["note"],
                "source_url": row["source_url"],
            }
        )

    return {
        "note": context["config"].get("legacy_view_note", "").strip(),
        "summary": {
            "row_count": total["row_count"] if total else 0,
            "school_count": total["school_count"] if total else 0,
            "returned_count": len(items),
        },
        "items": items,
    }


def fetch_candidate_rows(
    province_slug: str | None,
    score: int,
    min_score: int | None,
    year: int | None,
    school_keyword: str,
    major_keyword: str,
) -> list[sqlite3.Row]:
    context = ensure_database_ready(province_slug)
    params = {
        "max_score": score + 10,
        "min_score": min_score,
        "year": year,
        "school_keyword_like": f"%{school_keyword}%",
        "major_keyword_like": f"%{major_keyword}%",
    }
    where_parts = ["score <= :max_score"]
    if min_score is not None:
        where_parts.append("score >= :min_score")
    if year is not None:
        where_parts.append("year = :year")
    if school_keyword:
        where_parts.append(
            "(em.school_name LIKE :school_keyword_like OR COALESCE(NULLIF(sm.gaokao_school_name, ''), em.school_name) LIKE :school_keyword_like)"
        )
    if major_keyword:
        where_parts.append("major_name LIKE :major_keyword_like")
    where_clause = " AND ".join(where_parts)

    sql = f"""
        SELECT
            em.year,
            em.school_code,
            em.school_name AS school_name_official,
            COALESCE(NULLIF(sm.gaokao_school_name, ''), em.school_name) AS school_name,
            em.official_group_code,
            em.official_group_name,
            em.official_group_category,
            em.score,
            em.elective_info,
            em.major_code,
            em.major_name,
            em.major_name_short,
            em.major_category_level1,
            em.major_category_level2,
            em.major_category_level3,
            em.study_length,
            em.tuition,
            em.enrollment_count,
            em.zslx_name,
            em.source_url
        FROM eligible_majors em
        LEFT JOIN school_mappings sm
            ON sm.school_name_official = em.school_name
        WHERE {where_clause}
        ORDER BY em.score DESC, em.year DESC, school_name ASC, em.official_group_code ASC, em.major_name COLLATE NOCASE ASC
    """
    with get_connection(context["db_path"]) as conn:
        return conn.execute(sql, params).fetchall()


def build_major_history_index(rows: list[sqlite3.Row]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    history: dict[tuple[str, str, int], int] = {}
    for row in rows:
        major_key = clean_major_key(row["major_code"], row["major_name"])
        key = (row["school_name"], major_key, row["year"])
        score = row["score"]
        if key not in history or score < history[key]:
            history[key] = score

    grouped: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for (school_name, major_key, year), score in history.items():
        grouped.setdefault((school_name, major_key), []).append((year, score))

    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for key, values in grouped.items():
        result[key] = [{"year": year, "min_group_score": score} for year, score in sorted(values)]
    return result


def build_groups(
    rows: list[sqlite3.Row],
    user_score: int,
    favorite_schools: set[str],
) -> list[dict[str, Any]]:
    major_history_index = build_major_history_index(rows)
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in rows:
        key = (
            row["year"],
            row["school_code"],
            row["school_name"],
            row["official_group_code"],
            row["official_group_name"],
            row["score"],
        )
        if key not in grouped:
            tier, delta = classify_tier(user_score, row["score"])
            grouped[key] = {
                "year": row["year"],
                "school_code": row["school_code"],
                "school_name": row["school_name"],
                "official_group_code": row["official_group_code"],
                "official_group_name": row["official_group_name"],
                "official_group_category": row["official_group_category"],
                "score": row["score"],
                "score_delta": delta,
                "recommendation_tier": tier,
                "recommendation_hint": tier_description(tier),
                "elective_info": row["elective_info"],
                "source_url": row["source_url"],
                "is_favorite": row["school_name"] in favorite_schools,
                "majors": [],
            }
        grouped[key]["majors"].append(
            {
                "major_code": row["major_code"],
                "major_name": row["major_name"],
                "major_name_short": row["major_name_short"],
                "major_category_level1": row["major_category_level1"],
                "major_category_level2": row["major_category_level2"],
                "major_category_level3": row["major_category_level3"],
                "study_length": row["study_length"],
                "tuition": row["tuition"],
                "enrollment_count": row["enrollment_count"],
                "zslx_name": row["zslx_name"],
                "yearly_visible_group_scores": major_history_index.get(
                    (row["school_name"], clean_major_key(row["major_code"], row["major_name"])),
                    [],
                ),
            }
        )

    groups = list(grouped.values())
    for group in groups:
        group["major_count"] = len(group["majors"])

    groups.sort(
        key=lambda group: (
            {"冲": 0, "稳": 1, "保": 2}[group["recommendation_tier"]],
            -group["score"],
            -group["year"],
            group["school_name"],
            group["official_group_code"],
        )
    )
    return groups


def flatten_groups(groups: list[dict[str, Any]], user_score: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        for major in group["majors"]:
            rows.append(
                {
                    "年份": group["year"],
                    "推荐层级": group["recommendation_tier"],
                    "层级说明": group["recommendation_hint"],
                    "当前分数": user_score,
                    "投档线": group["score"],
                    "分差": group["score_delta"],
                    "院校代码": group["school_code"],
                    "学校": group["school_name"],
                    "专业组代码": group["official_group_code"],
                    "专业组名称": group["official_group_name"],
                    "专业组类别": group["official_group_category"],
                    "选科要求": group["elective_info"],
                    "专业代码": major["major_code"],
                    "专业名称": major["major_name"],
                    "专业简称": major["major_name_short"],
                    "专业层级1": major["major_category_level1"],
                    "专业层级2": major["major_category_level2"],
                    "专业层级3": major["major_category_level3"],
                    "学制": major["study_length"],
                    "学费": major["tuition"],
                    "计划数": major["enrollment_count"],
                    "招生类型": major["zslx_name"],
                    "历年可见最低专业组线": " / ".join(
                        f"{item['year']}:{item['min_group_score']}" for item in major["yearly_visible_group_scores"]
                    ),
                    "计划来源": group["source_url"],
                }
            )
    return rows


def summarize_groups(groups: list[dict[str, Any]]) -> dict[str, Any]:
    tier_counts = {"冲": 0, "稳": 0, "保": 0}
    school_count = len({group["school_name"] for group in groups})
    major_count = 0
    for group in groups:
        tier_counts[group["recommendation_tier"]] += 1
        major_count += group["major_count"]
    return {
        "school_count": school_count,
        "group_count": len(groups),
        "major_count": major_count,
        "tier_counts": tier_counts,
    }


def search_candidates(
    province_slug: str,
    score: int,
    min_score: int | None,
    year: int | None,
    school_keyword: str,
    major_keyword: str,
    group_limit: int,
    tier_filter: str,
    favorite_schools: set[str],
    favorites_only: bool,
) -> dict[str, Any]:
    rows = fetch_candidate_rows(province_slug, score, min_score, year, school_keyword, major_keyword)
    all_groups = build_groups(rows, score, favorite_schools)
    visible_groups = all_groups
    if favorites_only:
        visible_groups = [group for group in visible_groups if group["is_favorite"]]

    summary = summarize_groups(visible_groups)
    filtered_groups = visible_groups
    if tier_filter:
        filtered_groups = [group for group in filtered_groups if group["recommendation_tier"] == tier_filter]

    limited_groups = filtered_groups[:group_limit]
    return {
        "query": {
            "province": province_slug,
            "score": score,
            "min_score": min_score,
            "year": year,
            "school_keyword": school_keyword,
            "major_keyword": major_keyword,
            "group_limit": group_limit,
            "tier_filter": tier_filter,
            "favorites_only": favorites_only,
        },
        "summary": {
            **summary,
            "returned_group_count": len(limited_groups),
            "favorite_school_count": len(favorite_schools),
            "score_delta_explanation": "这里的分差 = 你的预估分 - 历史专业组投档线；正数表示高出历史线，负数表示低于历史线。",
            "major_score_note": "当前展示的是该专业在本库中可见的历年最低专业组投档线，不等于真实专业最低录取分。",
        },
        "groups": limited_groups,
    }


def export_candidates(
    province_slug: str,
    score: int,
    min_score: int | None,
    year: int | None,
    school_keyword: str,
    major_keyword: str,
    group_limit: int,
    tier_filter: str,
    favorite_schools: set[str],
    favorites_only: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = fetch_candidate_rows(province_slug, score, min_score, year, school_keyword, major_keyword)
    groups = build_groups(rows, score, favorite_schools)
    if favorites_only:
        groups = [group for group in groups if group["is_favorite"]]
    if tier_filter:
        groups = [group for group in groups if group["recommendation_tier"] == tier_filter]
    groups = groups[:group_limit]
    return flatten_groups(groups, score), summarize_groups(groups)


def build_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("无可导出数据\n")
    return output.getvalue().encode("utf-8-sig")


def build_xlsx_bytes(rows: list[dict[str, Any]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "检索结果"
    if rows:
        headers = list(rows[0].keys())
        worksheet.append(headers)
        for row in rows:
            worksheet.append([row.get(header, "") for header in headers])
        worksheet.freeze_panes = "A2"
    else:
        worksheet.append(["无可导出数据"])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def safe_filename(stem: str, suffix: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"_", "-", "."} else "_" for char in stem)
    return f"{cleaned}{suffix}"


class AdmissionsHandler(BaseHTTPRequestHandler):
    server_version = "AdmissionsFrontend/3.0"

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_common_headers("text/plain; charset=utf-8", 0)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in STATIC_FILES:
            self.serve_static(parsed.path)
            return
        if parsed.path == "/api/meta":
            self.handle_meta(parsed.query)
            return
        if parsed.path == "/api/search":
            self.handle_search(parsed.query)
            return
        if parsed.path == "/api/school-detail":
            self.handle_school_detail(parsed.query)
            return
        if parsed.path == "/api/legacy-school-lines":
            self.handle_legacy_school_lines(parsed.query)
            return
        if parsed.path == "/api/export":
            self.handle_export(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def parse_province_slug(self, raw_query: str) -> tuple[str | None, str | None]:
        slug = parse_qs(raw_query).get("province", [ACTIVE_PROVINCE_SLUG])[0].strip() or ACTIVE_PROVINCE_SLUG
        try:
            ensure_database_ready(slug)
        except FileNotFoundError as exc:
            return None, str(exc)
        except FileNotFoundError as exc:
            return None, str(exc)
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)
        return slug, None

    def parse_search_inputs(self, raw_query: str, export_mode: bool = False) -> tuple[dict[str, Any] | None, str | None]:
        query = parse_qs(raw_query)
        province_slug, province_error = self.parse_province_slug(raw_query)
        if province_error:
            return None, province_error

        try:
            score = int(query.get("score", ["450"])[0])
        except ValueError:
            return None, "score 必须是整数"
        if not 0 <= score <= 750:
            return None, "score 超出合理范围"

        min_score_value = query.get("min_score", [""])[0].strip()
        try:
            min_score = int(min_score_value) if min_score_value else None
        except ValueError:
            return None, "min_score 必须为空或为整数"
        if min_score is not None and not 0 <= min_score <= 750:
            return None, "min_score 超出合理范围"
        if min_score is not None and min_score > score + 10:
            return None, "min_score 不能高于预估分上浮 10 分后的上限"

        year_value = query.get("year", [""])[0].strip()
        try:
            year = int(year_value) if year_value else None
        except ValueError:
            return None, "year 必须为空或为年份整数"

        school_keyword = query.get("school", [""])[0].strip()
        major_keyword = query.get("major", [""])[0].strip()
        tier_filter = query.get("tier", [""])[0].strip()
        if tier_filter and tier_filter not in {"冲", "稳", "保"}:
            return None, "tier 只能是 冲、稳、保"

        try:
            default_limit = "5000" if export_mode else "36"
            group_limit = int(query.get("limit", [default_limit])[0])
        except ValueError:
            return None, "limit 必须是整数"
        group_limit = max(1, min(group_limit, 5000 if export_mode else 200))

        favorite_schools = {value.strip() for value in query.get("favorite_school", []) if value.strip()}
        favorites_only = query.get("favorites_only", ["0"])[0].strip() in {"1", "true", "True"}
        return {
            "province_slug": province_slug,
            "score": score,
            "min_score": min_score,
            "year": year,
            "school_keyword": school_keyword,
            "major_keyword": major_keyword,
            "group_limit": group_limit,
            "tier_filter": tier_filter,
            "favorite_schools": favorite_schools,
            "favorites_only": favorites_only,
        }, None

    def serve_static(self, request_path: str) -> None:
        relative_path, content_type = STATIC_FILES[request_path]
        file_path = FRONTEND_DIR / relative_path
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_common_headers(content_type, len(content))
        self.end_headers()
        self.wfile.write(content)

    def handle_meta(self, raw_query: str) -> None:
        province_slug, error = self.parse_province_slug(raw_query)
        if error:
            self.write_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return
        self.write_json(fetch_meta(province_slug))

    def handle_search(self, raw_query: str) -> None:
        parsed, error = self.parse_search_inputs(raw_query)
        if error:
            self.write_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return
        payload = search_candidates(
            parsed["province_slug"],
            parsed["score"],
            parsed["min_score"],
            parsed["year"],
            parsed["school_keyword"],
            parsed["major_keyword"],
            parsed["group_limit"],
            parsed["tier_filter"],
            parsed["favorite_schools"],
            parsed["favorites_only"],
        )
        self.write_json(payload)

    def handle_school_detail(self, raw_query: str) -> None:
        query = parse_qs(raw_query)
        province_slug, error = self.parse_province_slug(raw_query)
        if error:
            self.write_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return

        school_name = query.get("school_name", [""])[0].strip()
        if not school_name:
            self.write_json({"error": "school_name 不能为空"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            user_score = int(query.get("score", ["450"])[0])
        except ValueError:
            self.write_json({"error": "score 必须是整数"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = fetch_school_detail(school_name, user_score, province_slug)
        except KeyError:
            self.write_json({"error": "未找到该学校的详情数据"}, HTTPStatus.NOT_FOUND)
            return
        self.write_json(payload)

    def handle_legacy_school_lines(self, raw_query: str) -> None:
        parsed, error = self.parse_search_inputs(raw_query)
        if error:
            self.write_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return
        payload = fetch_legacy_school_lines(
            parsed["province_slug"],
            parsed["score"],
            parsed["min_score"],
            parsed["school_keyword"],
            parsed["group_limit"],
        )
        self.write_json(payload)

    def handle_export(self, raw_query: str) -> None:
        parsed, error = self.parse_search_inputs(raw_query, export_mode=True)
        if error:
            self.write_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return

        export_format = parse_qs(raw_query).get("format", ["csv"])[0].strip().lower()
        if export_format not in {"csv", "xlsx"}:
            self.write_json({"error": "format 只能是 csv 或 xlsx"}, HTTPStatus.BAD_REQUEST)
            return

        rows, summary = export_candidates(
            parsed["province_slug"],
            parsed["score"],
            parsed["min_score"],
            parsed["year"],
            parsed["school_keyword"],
            parsed["major_keyword"],
            parsed["group_limit"],
            parsed["tier_filter"],
            parsed["favorite_schools"],
            parsed["favorites_only"],
        )
        if export_format == "csv":
            content = build_csv_bytes(rows)
            content_type = "text/csv; charset=utf-8"
            suffix = ".csv"
        else:
            content = build_xlsx_bytes(rows)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            suffix = ".xlsx"

        tier_part = parsed["tier_filter"] or "all"
        filename = safe_filename(
            f"{parsed['province_slug']}_admissions_{parsed['score']}_{tier_part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            suffix,
        )
        self.send_response(HTTPStatus.OK)
        self.send_common_headers(content_type, len(content))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_common_headers("application/json; charset=utf-8", len(content))
        self.end_headers()
        self.wfile.write(content)

    def send_common_headers(self, content_type: str, content_length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the admissions frontend.")
    parser.add_argument("--province", default=DEFAULT_PROVINCE_SLUG)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    configure_runtime(args.province)
    ensure_database_ready(args.province)

    server = ThreadingHTTPServer((args.host, args.port), AdmissionsHandler)
    print(f"Serving {args.province} default on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
