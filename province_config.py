from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configs" / "provinces"
DEFAULT_PROVINCE_SLUG = "hunan"


def load_province_config(slug: str) -> dict[str, Any]:
    config_path = CONFIG_DIR / f"{slug}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"province config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def list_province_slugs() -> list[str]:
    return sorted(path.stem for path in CONFIG_DIR.glob("*.json"))


def build_year_range_text(config: dict[str, Any]) -> str:
    years = sorted(int(year) for year in config.get("official_sources", {}).keys())
    if not years:
        return ""
    if len(years) == 1:
        return str(years[0])
    return f"{years[0]}-{years[-1]}"


def build_scope_summary(config: dict[str, Any]) -> str:
    province_name = config.get("province_name", "")
    subjects = " / ".join(config.get("user_subjects", []))
    year_range = build_year_range_text(config)
    score_range = config.get("score_range", {})
    score_min = score_range.get("min", "")
    score_max = score_range.get("max", "")

    parts = [part for part in (f"{province_name}考生" if province_name else "", subjects, year_range) if part]
    if score_min != "" and score_max != "":
        parts.append(f"{score_min}-{score_max} 分")
    return " · ".join(parts)
