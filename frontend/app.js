const STORAGE_KEYS = {
  apiBase: "hunanAdmissions.apiBase",
  province: "hunanAdmissions.province",
  favoritesPrefix: "hunanAdmissions.favoriteSchools.",
};

const state = {
  apiBase: "",
  meta: null,
  currentPayload: null,
  currentTier: "",
  currentProvince: "",
  favorites: new Set(),
  schoolDetailCache: new Map(),
};

const els = {
  appEyebrow: document.querySelector("#appEyebrow"),
  appTitle: document.querySelector("#appTitle"),
  heroKicker: document.querySelector("#heroKicker"),
  heroTitle: document.querySelector("#heroTitle"),
  heroText: document.querySelector("#heroText"),
  tierNoteChong: document.querySelector("#tierNoteChong"),
  tierNoteWen: document.querySelector("#tierNoteWen"),
  tierNoteBao: document.querySelector("#tierNoteBao"),
  provinceSelect: document.querySelector("#provinceSelect"),
  apiBaseInput: document.querySelector("#apiBaseInput"),
  connectButton: document.querySelector("#connectButton"),
  connectionState: document.querySelector("#connectionState"),
  datasetMeta: document.querySelector("#datasetMeta"),
  searchForm: document.querySelector("#searchForm"),
  scoreInput: document.querySelector("#scoreInput"),
  minScoreInput: document.querySelector("#minScoreInput"),
  yearSelect: document.querySelector("#yearSelect"),
  schoolInput: document.querySelector("#schoolInput"),
  majorInput: document.querySelector("#majorInput"),
  limitInput: document.querySelector("#limitInput"),
  favoritesOnlyCheckbox: document.querySelector("#favoritesOnlyCheckbox"),
  resetButton: document.querySelector("#resetButton"),
  summaryCards: document.querySelector("#summaryCards"),
  tierTabs: document.querySelector("#tierTabs"),
  results: document.querySelector("#results"),
  statusText: document.querySelector("#statusText"),
  favoritesPanel: document.querySelector("#favoritesPanel"),
  favoriteCountText: document.querySelector("#favoriteCountText"),
  exportCsvButton: document.querySelector("#exportCsvButton"),
  exportExcelButton: document.querySelector("#exportExcelButton"),
  exportFavoritesCsvButton: document.querySelector("#exportFavoritesCsvButton"),
  exportFavoritesExcelButton: document.querySelector("#exportFavoritesExcelButton"),
  usageHintApi: document.querySelector("#usageHintApi"),
  dataScopePanel: document.querySelector("#dataScopePanel"),
  legacySchoolLinesSection: document.querySelector("#legacySchoolLinesSection"),
  legacySchoolLinesSummary: document.querySelector("#legacySchoolLinesSummary"),
  legacySchoolLinesResults: document.querySelector("#legacySchoolLinesResults"),
  favoriteTemplate: document.querySelector("#favoriteTemplate"),
  groupTemplate: document.querySelector("#groupTemplate"),
  majorTemplate: document.querySelector("#majorTemplate"),
  legacySchoolLineTemplate: document.querySelector("#legacySchoolLineTemplate"),
  schoolDetailDialog: document.querySelector("#schoolDetailDialog"),
  detailDialogEyebrow: document.querySelector("#detailDialogEyebrow"),
  detailDialogTitle: document.querySelector("#detailDialogTitle"),
  detailDialogClose: document.querySelector("#detailDialogClose"),
  detailDialogSummary: document.querySelector("#detailDialogSummary"),
  detailDialogChart: document.querySelector("#detailDialogChart"),
  detailDialogYears: document.querySelector("#detailDialogYears"),
  detailDialogNote: document.querySelector("#detailDialogNote"),
};

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function normalizeApiBase(value) {
  return value.trim().replace(/\/+$/, "");
}

function defaultApiBase() {
  if (window.location.protocol.startsWith("http")) {
    return normalizeApiBase(window.location.origin);
  }
  return normalizeApiBase(localStorage.getItem(STORAGE_KEYS.apiBase) || "http://127.0.0.1:5500");
}

function getUrlProvince() {
  const value = new URLSearchParams(window.location.search).get("province");
  return value?.trim() || "";
}

function defaultProvince() {
  return getUrlProvince() || localStorage.getItem(STORAGE_KEYS.province) || "hunan";
}

function favoriteStorageKey(provinceSlug) {
  return `${STORAGE_KEYS.favoritesPrefix}${provinceSlug}`;
}

function loadFavorites() {
  try {
    const raw = localStorage.getItem(favoriteStorageKey(state.currentProvince)) || "[]";
    const parsed = JSON.parse(raw);
    state.favorites = new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    state.favorites = new Set();
  }
}

function saveFavorites() {
  localStorage.setItem(
    favoriteStorageKey(state.currentProvince),
    JSON.stringify([...state.favorites].sort()),
  );
}

function syncProvinceUrl(provinceSlug) {
  const url = new URL(window.location.href);
  url.searchParams.set("province", provinceSlug);
  history.replaceState(null, "", url);
}

function setConnectionState(text, type = "") {
  els.connectionState.textContent = text;
  els.connectionState.dataset.state = type;
}

function createTag(text, className = "") {
  const tag = document.createElement("span");
  tag.className = `tag ${className}`.trim();
  tag.textContent = text;
  return tag;
}

function clampScore(value, minValue, maxValue) {
  if (!Number.isFinite(value)) {
    return Math.max(minValue, Math.min(450, maxValue));
  }
  return Math.max(minValue, Math.min(value, maxValue));
}

function renderProvinceOptions(provinces, selectedSlug) {
  els.provinceSelect.innerHTML = "";
  for (const province of provinces) {
    const option = document.createElement("option");
    option.value = province.slug;
    option.textContent = province.database_ready
      ? `${province.name} ${province.year_range}`
      : `${province.name}（数据库未构建）`;
    option.disabled = !province.database_ready;
    option.selected = province.slug === selectedSlug;
    els.provinceSelect.append(option);
  }
}

function renderChrome(meta) {
  document.title = meta.app_title;
  els.appEyebrow.textContent = meta.app_eyebrow;
  els.appTitle.textContent = meta.app_title;
  els.heroKicker.textContent = meta.hero_kicker;
  els.heroTitle.textContent = meta.hero_title;
  els.heroText.textContent = meta.hero_text;
  els.tierNoteChong.textContent = `冲：${meta.tier_rules["冲"]}`;
  els.tierNoteWen.textContent = `稳：${meta.tier_rules["稳"]}`;
  els.tierNoteBao.textContent = `保：${meta.tier_rules["保"]}`;
  els.usageHintApi.textContent =
    "如果页面是直接双击 HTML 打开的，请把上面的 API 地址填成你启动服务的地址，比如 http://127.0.0.1:5500，再点“连接服务”。";
}

function renderMeta(meta) {
  els.datasetMeta.innerHTML = `
    <div class="metric-card">
      <span>学校覆盖</span>
      <strong>${formatNumber(meta.school_count)}</strong>
    </div>
    <div class="metric-card">
      <span>专业记录</span>
      <strong>${formatNumber(meta.major_rows)}</strong>
    </div>
    <div class="metric-card">
      <span>分数范围</span>
      <strong>${meta.score_min}-${meta.score_max}</strong>
    </div>
    <div class="metric-card metric-card-compact">
      <span>当前范围</span>
      <strong>${meta.scope_summary}</strong>
    </div>
  `;
}

function renderDataScope(meta) {
  const currentSources = (meta.current_sources || [])
    .map(
      (source) => `
        <li>
          <strong>${source.year}</strong>
          <span>${source.title}</span>
          <a href="${source.landing_url}" target="_blank" rel="noreferrer">公告页</a>
          <a href="${source.file_url}" target="_blank" rel="noreferrer">源文件</a>
        </li>
      `,
    )
    .join("");

  const legacyNotes = (meta.legacy_year_notes || [])
    .map(
      (note) => `
        <article class="scope-block scope-block-legacy">
          <div class="scope-block-head">
            <span class="legacy-badge">${note.year}</span>
            <strong>${note.title}</strong>
          </div>
          <p>${note.summary}</p>
          <div class="scope-links">
            ${(note.sources || [])
              .map(
                (source) =>
                  `<a href="${source.url}" target="_blank" rel="noreferrer">${source.label}</a>`,
              )
              .join("")}
          </div>
        </article>
      `,
    )
    .join("");

  els.dataScopePanel.innerHTML = `
    <article class="scope-block">
      <div class="scope-block-head">
        <strong>当前检索范围</strong>
        <span class="scope-badge">${meta.configured_year_range}</span>
      </div>
      <p>${meta.search_data_note}</p>
      <p class="scope-muted">${meta.scope_summary}</p>
      <ul class="scope-source-list">${currentSources}</ul>
    </article>
    ${
      legacyNotes ||
      `
        <article class="scope-block">
          <div class="scope-block-head">
            <strong>历史数据说明</strong>
            <span class="scope-badge">当前无额外拆分</span>
          </div>
          <p>当前省份的历史年份口径与搜索结果一致，没有单独拆出来的旧批次说明。</p>
        </article>
      `
    }
  `;
}

function renderLegacySchoolLines(payload, meta) {
  const section = els.legacySchoolLinesSection;
  const summaryNode = els.legacySchoolLinesSummary;
  const resultsNode = els.legacySchoolLinesResults;
  if (!payload || !payload.items?.length) {
    section.hidden = true;
    summaryNode.innerHTML = "";
    resultsNode.innerHTML = "";
    return;
  }

  section.hidden = false;
  summaryNode.innerHTML = `
    <div class="summary-card">
      <span>匹配学校</span>
      <strong>${formatNumber(payload.summary.school_count)}</strong>
    </div>
    <div class="summary-card">
      <span>匹配学校线</span>
      <strong>${formatNumber(payload.summary.row_count)}</strong>
    </div>
    <div class="summary-card metric-card-compact">
      <span>口径说明</span>
      <strong>${payload.note || meta?.legacy_view_note || "学校级批次线，仅供院校门槛参考。"}</strong>
    </div>
  `;

  resultsNode.innerHTML = "";
  payload.items.forEach((item) => {
    const node = els.legacySchoolLineTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".legacy-line-year").textContent = `${item.year} 年 · ${item.batch}`;
    node.querySelector(".legacy-line-school").textContent = item.school_name;
    node.querySelector(".legacy-line-score").textContent = `学校线 ${item.score}`;

    const metaNode = node.querySelector(".legacy-line-meta");
    metaNode.append(createTag(item.subject_type || "理工类"));
    metaNode.append(createTag(`${item.recommendation_tier}档`));
    metaNode.append(createTag(item.score_delta >= 0 ? `高出 ${item.score_delta}` : `低于 ${Math.abs(item.score_delta)}`));
    if (item.rank_value) {
      metaNode.append(createTag(`位次 ${item.rank_value}`));
    }

    node.querySelector(".legacy-line-note").textContent =
      item.note || payload.note || "这是学校级批次投档线，不代表专业组线或专业最低录取分。";
    resultsNode.append(node);
  });
}

function renderYearOptions(years) {
  els.yearSelect.innerHTML = '<option value="">全部年份</option>';
  for (const year of years) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = `${year} 年`;
    els.yearSelect.append(option);
  }
}

function renderSummary(summary, query) {
  const items = [
    { label: "你的预估分", value: `${query.score} 分` },
    { label: "最低分条件", value: query.min_score ? `${query.min_score} 分` : "未设置" },
    { label: "年份条件", value: query.year ? `${query.year} 年` : "全部年份" },
    { label: "匹配学校", value: `${formatNumber(summary.school_count)} 所` },
    { label: "匹配专业组", value: `${formatNumber(summary.group_count)} 个` },
    { label: "匹配专业", value: `${formatNumber(summary.major_count)} 个` },
    { label: "本页显示", value: `${formatNumber(summary.returned_group_count)} 个组` },
    { label: "已收藏学校", value: `${formatNumber(summary.favorite_school_count)} 所` },
  ];

  els.summaryCards.innerHTML = items
    .map(
      (item) => `
        <div class="summary-card">
          <span>${item.label}</span>
          <strong>${item.value}</strong>
        </div>
      `,
    )
    .join("");

  els.summaryCards.insertAdjacentHTML(
    "beforeend",
    `
      <div class="summary-note">
        <p>${summary.score_delta_explanation}</p>
        <p>${summary.major_score_note}</p>
      </div>
    `,
  );
}

function renderTierTabs(summary) {
  const tiers = [
    { key: "", label: "全部" },
    { key: "冲", label: `冲 ${summary.tier_counts["冲"]}` },
    { key: "稳", label: `稳 ${summary.tier_counts["稳"]}` },
    { key: "保", label: `保 ${summary.tier_counts["保"]}` },
  ];

  els.tierTabs.innerHTML = "";
  for (const tier of tiers) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tier-tab";
    button.dataset.tier = tier.key;
    if (state.currentTier === tier.key) {
      button.dataset.active = "true";
    }
    button.textContent = tier.label;
    els.tierTabs.append(button);
  }
}

function renderFavoritesPanel() {
  const favorites = [...state.favorites].sort((a, b) => a.localeCompare(b, "zh-CN"));
  els.favoriteCountText.textContent = `${favorites.length} 所`;
  els.favoritesPanel.innerHTML = "";

  if (!favorites.length) {
    els.favoritesPanel.innerHTML = `
      <div class="empty-mini">
        <p>还没有收藏学校。点结果卡右上角的星标即可收藏。</p>
      </div>
    `;
    return;
  }

  for (const schoolName of favorites) {
    const node = els.favoriteTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".favorite-link").textContent = schoolName;
    node.querySelector(".favorite-link").dataset.school = schoolName;
    node.querySelector(".favorite-remove").dataset.school = schoolName;
    els.favoritesPanel.append(node);
  }
}

function buildMajorHistoryLabel(query) {
  return query.year ? `${query.year} 年可见专业组线` : "历年可见最低专业组线";
}

function renderMajors(container, majors, query) {
  const historyLabel = buildMajorHistoryLabel(query);
  for (const major of majors) {
    const node = els.majorTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".major-name").textContent = major.major_name;
    node.querySelector(".major-code").textContent = major.major_code ? `代码 ${major.major_code}` : "代码待补";

    const tags = [
      major.study_length,
      major.tuition ? `学费 ${major.tuition}` : "",
      major.enrollment_count ? `计划 ${major.enrollment_count}` : "",
      major.zslx_name,
      major.major_category_level2,
      major.major_category_level3,
    ].filter(Boolean);
    const tagsContainer = node.querySelector(".major-tags");
    for (const tag of tags) {
      tagsContainer.append(createTag(tag));
    }

    if (major.yearly_visible_group_scores?.length) {
      const history = document.createElement("div");
      history.className = "major-history";
      history.innerHTML = `
        <span class="major-history-label">${historyLabel}</span>
        <div class="major-history-values">
          ${major.yearly_visible_group_scores
            .map((item) => `<span class="tag tag-soft">${item.year} 年 ${item.min_group_score} 分</span>`)
            .join("")}
        </div>
      `;
      node.append(history);
    }

    container.append(node);
  }
}

function buildTrendChart(yearly) {
  if (!yearly.length) {
    return '<div class="empty-mini"><p>暂无趋势数据</p></div>';
  }

  const width = 720;
  const height = 240;
  const paddingX = 44;
  const paddingTop = 24;
  const paddingBottom = 36;
  const minScore = Math.min(...yearly.map((item) => item.min_score));
  const maxScore = Math.max(...yearly.map((item) => item.max_score));
  const scoreSpan = Math.max(maxScore - minScore, 1);
  const stepX = yearly.length > 1 ? (width - paddingX * 2) / (yearly.length - 1) : 0;

  const yFor = (score) => {
    const ratio = (score - minScore) / scoreSpan;
    return height - paddingBottom - ratio * (height - paddingTop - paddingBottom);
  };

  const avgPoints = yearly
    .map((item, index) => `${paddingX + index * stepX},${yFor(item.avg_score)}`)
    .join(" ");

  const guideScores = Array.from({ length: 4 }, (_, index) => Math.round(minScore + ((maxScore - minScore) * index) / 3));
  const guides = guideScores
    .map((score) => {
      const y = yFor(score);
      return `
        <line x1="${paddingX}" y1="${y}" x2="${width - paddingX}" y2="${y}" class="chart-guide-line" />
        <text x="${paddingX - 10}" y="${y + 4}" class="chart-axis-label chart-axis-left">${score}</text>
      `;
    })
    .join("");

  const yearLabels = yearly
    .map((item, index) => {
      const x = paddingX + index * stepX;
      return `<text x="${x}" y="${height - 10}" class="chart-axis-label chart-axis-bottom">${item.year}</text>`;
    })
    .join("");

  const ranges = yearly
    .map((item, index) => {
      const x = paddingX + index * stepX;
      return `
        <line x1="${x}" y1="${yFor(item.max_score)}" x2="${x}" y2="${yFor(item.min_score)}" class="chart-range-line" />
        <circle cx="${x}" cy="${yFor(item.min_score)}" r="4" class="chart-range-dot" />
        <circle cx="${x}" cy="${yFor(item.max_score)}" r="4" class="chart-range-dot" />
        <circle cx="${x}" cy="${yFor(item.avg_score)}" r="5" class="chart-avg-dot" />
      `;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="学校分数线趋势图">
      ${guides}
      <polyline points="${avgPoints}" class="chart-avg-line" />
      ${ranges}
      ${yearLabels}
    </svg>
  `;
}

function renderSchoolDetail(detail) {
  const yearRange = detail.yearly.map((item) => item.year);
  const yearLabel = yearRange.length ? `${Math.min(...yearRange)}-${Math.max(...yearRange)}` : "";
  els.detailDialogEyebrow.textContent = `${detail.province_name} · 学校代码 ${detail.school_code} · 参考分 ${detail.user_score}`;
  els.detailDialogTitle.textContent = `${detail.school_name} ${yearLabel} 分数线趋势`;
  els.detailDialogSummary.innerHTML = `
    <div class="detail-summary-card">
      <span>覆盖年份</span>
      <strong>${detail.yearly.length} 年</strong>
    </div>
    <div class="detail-summary-card">
      <span>最高投档线</span>
      <strong>${Math.max(...detail.yearly.map((item) => item.max_score))}</strong>
    </div>
    <div class="detail-summary-card">
      <span>最低投档线</span>
      <strong>${Math.min(...detail.yearly.map((item) => item.min_score))}</strong>
    </div>
    <div class="detail-summary-card">
      <span>专业组总数</span>
      <strong>${detail.yearly.reduce((sum, item) => sum + item.group_count, 0)}</strong>
    </div>
  `;
  els.detailDialogChart.innerHTML = buildTrendChart(detail.yearly);
  els.detailDialogYears.innerHTML = detail.yearly
    .map(
      (item) => `
        <section class="detail-year-card">
          <div class="detail-year-head">
            <h4>${item.year} 年</h4>
            <div class="detail-year-stats">
              <span>最低 ${item.min_score}</span>
              <span>均值 ${item.avg_score}</span>
              <span>最高 ${item.max_score}</span>
              <span>专业组 ${item.group_count}</span>
            </div>
          </div>
          <div class="detail-group-list">
            ${item.groups
              .map(
                (group) => `
                  <div class="detail-group-item">
                    <div class="detail-group-main">
                      <strong>${group.official_group_name}</strong>
                      <span>${group.official_group_category}</span>
                    </div>
                    <div class="detail-group-side">
                      <span>投档线 ${group.score}</span>
                      <span>${group.recommendation_tier}档 / ${group.score_delta >= 0 ? `高出历史线 ${group.score_delta}` : `低于历史线 ${Math.abs(group.score_delta)}`}</span>
                      <span>${group.major_count} 个专业</span>
                    </div>
                    <div class="detail-group-meta">
                      <span>${group.elective_info || "选科信息待补"}</span>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        </section>
      `,
    )
    .join("");
  if (detail.legacy_school_lines?.length) {
    els.detailDialogYears.insertAdjacentHTML(
      "beforeend",
      detail.legacy_school_lines
        .map(
          (item) => `
            <section class="detail-year-card detail-year-card-legacy">
              <div class="detail-year-head">
                <h4>${item.year} 年学校级批次线</h4>
                <div class="detail-year-stats">
                  <span>最低 ${item.min_score}</span>
                  <span>最高 ${item.max_score}</span>
                  <span>记录 ${item.lines.length}</span>
                </div>
              </div>
              <div class="detail-group-list">
                ${item.lines
                  .map(
                    (line) => `
                      <div class="detail-group-item detail-group-item-legacy">
                        <div class="detail-group-main">
                          <strong>${line.batch}</strong>
                          <span>${line.subject_type}</span>
                        </div>
                        <div class="detail-group-side">
                          <span>学校线 ${line.score}</span>
                          <span>${line.recommendation_tier}档 / ${line.score_delta >= 0 ? `高出 ${line.score_delta}` : `低于 ${Math.abs(line.score_delta)}`}</span>
                          <span>${line.rank_value ? `位次 ${line.rank_value}` : "位次待补"}</span>
                        </div>
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            </section>
          `,
        )
        .join(""),
    );
  }
  els.detailDialogNote.textContent = detail.note;
  if (detail.legacy_school_line_note) {
    els.detailDialogNote.textContent = `${detail.note} ${detail.legacy_school_line_note}`;
  }
}

async function openSchoolDetail(schoolName) {
  const cacheKey = `${state.currentProvince}::${schoolName}::${els.scoreInput.value.trim()}`;
  let detail = state.schoolDetailCache.get(cacheKey);
  if (!detail) {
    els.statusText.textContent = `正在加载 ${schoolName} 详情…`;
    detail = await fetchJson(
      "/api/school-detail",
      new URLSearchParams({
        province: state.currentProvince,
        school_name: schoolName,
        score: els.scoreInput.value.trim(),
      }),
    );
    state.schoolDetailCache.set(cacheKey, detail);
  }
  renderSchoolDetail(detail);
  els.schoolDetailDialog.showModal();
  els.statusText.textContent = `已打开 ${schoolName} 详情`;
}

function renderResults(payload) {
  state.currentPayload = payload;
  renderSummary(payload.summary, payload.query);
  renderTierTabs(payload.summary);
  els.results.innerHTML = "";

  if (!payload.groups.length) {
    const reason = payload.query.favorites_only
      ? "当前开启了“只看已收藏学校”，但收藏学校里没有符合条件的结果。"
      : "没有查到符合条件的结果，可以试试调整分数、年份或关键词。";
    els.results.innerHTML = `
      <div class="empty-state">
        <h3>暂时没有结果</h3>
        <p>${reason}</p>
      </div>
    `;
    return;
  }

  payload.groups.forEach((group, index) => {
    const node = els.groupTemplate.content.firstElementChild.cloneNode(true);
    node.style.animationDelay = `${Math.min(index * 35, 420)}ms`;
    node.querySelector(".school-year").textContent = `${group.year} 年`;
    node.querySelector(".school-name").textContent = group.school_name;

    const favoriteButton = node.querySelector(".favorite-star");
    favoriteButton.dataset.school = group.school_name;
    favoriteButton.dataset.favorite = group.is_favorite ? "true" : "false";
    favoriteButton.textContent = group.is_favorite ? "★ 已收藏" : "☆ 收藏";

    node.querySelector(".score-badge").textContent = `专业组投档线 ${group.score}`;
    node.querySelector(".tier-badge").textContent = `${group.recommendation_tier}档`;
    node.querySelector(".tier-badge").dataset.tier = group.recommendation_tier;
    node.querySelector(".delta-badge").textContent =
      group.score_delta >= 0 ? `高出历史线 ${group.score_delta}` : `低于历史线 ${Math.abs(group.score_delta)}`;

    const meta = node.querySelector(".school-meta");
    meta.append(createTag(group.official_group_name));
    meta.append(createTag(group.official_group_category));
    meta.append(createTag(group.elective_info || "选科信息待补"));
    meta.append(createTag(`专业 ${group.major_count} 个`));
    meta.append(createTag(group.recommendation_hint, "tag-soft"));
    node.querySelector(".detail-button").dataset.school = group.school_name;

    renderMajors(node.querySelector(".major-list"), group.majors, payload.query);
    els.results.append(node);
  });
}

function buildSearchParams({ exportMode = false, favoritesOnlyOverride = null } = {}) {
  const params = new URLSearchParams();
  params.set("province", state.currentProvince);
  params.set("score", els.scoreInput.value.trim());
  if (els.minScoreInput.value.trim()) {
    params.set("min_score", els.minScoreInput.value.trim());
  }
  if (els.yearSelect.value.trim()) {
    params.set("year", els.yearSelect.value.trim());
  }
  if (els.schoolInput.value.trim()) {
    params.set("school", els.schoolInput.value.trim());
  }
  if (els.majorInput.value.trim()) {
    params.set("major", els.majorInput.value.trim());
  }
  params.set(
    "limit",
    exportMode ? String(Math.max(state.currentPayload?.summary.group_count || 200, 200)) : els.limitInput.value.trim(),
  );
  if (state.currentTier) {
    params.set("tier", state.currentTier);
  }

  const favoritesOnly = favoritesOnlyOverride ?? els.favoritesOnlyCheckbox.checked;
  if (favoritesOnly) {
    params.set("favorites_only", "1");
  }
  for (const schoolName of [...state.favorites].sort()) {
    params.append("favorite_school", schoolName);
  }
  return params;
}

function validateScoreInputs() {
  const scoreText = els.scoreInput.value.trim();
  if (!scoreText) {
    throw new Error("请先填写预估分");
  }

  const score = Number(scoreText);
  if (!Number.isFinite(score)) {
    throw new Error("预估分必须是数字");
  }

  const minScoreText = els.minScoreInput.value.trim();
  if (!minScoreText) {
    return;
  }

  const minScore = Number(minScoreText);
  if (!Number.isFinite(minScore)) {
    throw new Error("最低分必须是数字");
  }
  if (minScore > score + 10) {
    throw new Error("最低分不能高于预估分上浮 10 分后的上限");
  }
}

async function fetchJson(path, params = null) {
  const url = new URL(`${state.apiBase}${path}`);
  if (params) {
    url.search = params.toString();
  }
  const response = await fetch(url.toString());
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

async function connectAndLoadMeta() {
  state.apiBase = normalizeApiBase(els.apiBaseInput.value || defaultApiBase());
  state.currentProvince = (els.provinceSelect.value || state.currentProvince || defaultProvince()).trim();
  els.apiBaseInput.value = state.apiBase;
  localStorage.setItem(STORAGE_KEYS.apiBase, state.apiBase);
  localStorage.setItem(STORAGE_KEYS.province, state.currentProvince);
  syncProvinceUrl(state.currentProvince);

  setConnectionState("连接中…", "pending");
  const meta = await fetchJson("/api/meta", new URLSearchParams({ province: state.currentProvince }));
  state.meta = meta;
  state.currentProvince = meta.province_slug;
  localStorage.setItem(STORAGE_KEYS.province, state.currentProvince);
  syncProvinceUrl(state.currentProvince);

  renderProvinceOptions(meta.available_provinces, state.currentProvince);
  renderChrome(meta);
  renderMeta(meta);
  renderDataScope(meta);
  renderYearOptions(meta.years);

  const configuredMin = meta.configured_score_min ?? meta.score_min ?? 0;
  const configuredMax = meta.configured_score_max ?? meta.score_max ?? 750;
  els.scoreInput.min = configuredMin;
  els.scoreInput.max = configuredMax;
  els.minScoreInput.min = configuredMin;
  els.minScoreInput.max = configuredMax;

  els.scoreInput.value = String(clampScore(Number(els.scoreInput.value || 450), configuredMin, configuredMax));
  if (els.minScoreInput.value.trim()) {
    els.minScoreInput.value = String(
      clampScore(Number(els.minScoreInput.value), configuredMin, Math.min(configuredMax, Number(els.scoreInput.value) + 10)),
    );
  }

  loadFavorites();
  renderFavoritesPanel();
  setConnectionState("已连接", "ok");
}

async function search() {
  validateScoreInputs();
  els.statusText.textContent = "正在检索…";
  const payload = await fetchJson("/api/search", buildSearchParams());
  const legacyPayload = await fetchJson("/api/legacy-school-lines", buildSearchParams());
  renderResults(payload);
  renderLegacySchoolLines(legacyPayload, state.meta);
  els.statusText.textContent = `已返回 ${payload.summary.returned_group_count} 个专业组`;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportResults(format, favoritesOnly) {
  validateScoreInputs();
  const params = buildSearchParams({ exportMode: true, favoritesOnlyOverride: favoritesOnly });
  params.set("format", format);
  const url = new URL(`${state.apiBase}/api/export`);
  url.search = params.toString();

  els.statusText.textContent = `正在导出 ${format.toUpperCase()}…`;
  const response = await fetch(url.toString());
  if (!response.ok) {
    let message = "导出失败";
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const provinceName = state.meta?.province_name || state.currentProvince;
  const fileName = favoritesOnly
    ? `${provinceName}_收藏学校.${format === "csv" ? "csv" : "xlsx"}`
    : `${provinceName}_检索结果.${format === "csv" ? "csv" : "xlsx"}`;
  downloadBlob(blob, fileName);
  els.statusText.textContent = "导出完成";
}

function toggleFavorite(schoolName) {
  if (state.favorites.has(schoolName)) {
    state.favorites.delete(schoolName);
  } else {
    state.favorites.add(schoolName);
  }
  saveFavorites();
  renderFavoritesPanel();
}

function resetSearchForm() {
  const minValue = Number(els.scoreInput.min || 0);
  const maxValue = Number(els.scoreInput.max || 750);
  els.scoreInput.value = String(clampScore(450, minValue, maxValue));
  els.minScoreInput.value = "";
  els.yearSelect.value = "";
  els.schoolInput.value = "";
  els.majorInput.value = "";
  els.limitInput.value = "24";
  els.favoritesOnlyCheckbox.checked = false;
  state.currentTier = "";
  state.schoolDetailCache.clear();
}

function showError(error) {
  setConnectionState("连接失败", "error");
  els.statusText.textContent = error.message;
  els.results.innerHTML = `
    <div class="empty-state">
      <h3>页面没有连上查询服务</h3>
      <p>${error.message}</p>
      <p>请确认你打开的是服务地址页面，或者把上方 API 地址填成你启动服务的地址，例如 http://127.0.0.1:5500。</p>
    </div>
  `;
  renderLegacySchoolLines(null, state.meta);
}

async function switchProvince(provinceSlug) {
  state.currentProvince = provinceSlug;
  state.currentTier = "";
  state.schoolDetailCache.clear();
  state.currentPayload = null;
  try {
    await connectAndLoadMeta();
    await search();
  } catch (error) {
    showError(error);
  }
}

els.connectButton.addEventListener("click", async () => {
  try {
    await connectAndLoadMeta();
    await search();
  } catch (error) {
    showError(error);
  }
});

els.provinceSelect.addEventListener("change", async () => {
  await switchProvince(els.provinceSelect.value);
});

els.searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await search();
  } catch (error) {
    showError(error);
  }
});

els.resetButton.addEventListener("click", async () => {
  resetSearchForm();
  try {
    await search();
  } catch (error) {
    showError(error);
  }
});

els.tierTabs.addEventListener("click", async (event) => {
  const button = event.target.closest(".tier-tab");
  if (!button) {
    return;
  }
  state.currentTier = button.dataset.tier || "";
  try {
    await search();
  } catch (error) {
    showError(error);
  }
});

els.favoritesPanel.addEventListener("click", async (event) => {
  const schoolButton = event.target.closest(".favorite-link");
  if (schoolButton) {
    els.schoolInput.value = schoolButton.dataset.school || "";
    try {
      await search();
    } catch (error) {
      showError(error);
    }
    return;
  }

  const removeButton = event.target.closest(".favorite-remove");
  if (!removeButton) {
    return;
  }
  toggleFavorite(removeButton.dataset.school || "");
  if (state.currentPayload) {
    try {
      await search();
    } catch (error) {
      showError(error);
    }
  }
});

els.results.addEventListener("click", async (event) => {
  const favoriteButton = event.target.closest(".favorite-star");
  if (favoriteButton) {
    toggleFavorite(favoriteButton.dataset.school || "");
    try {
      await search();
    } catch (error) {
      showError(error);
    }
    return;
  }

  const detailButton = event.target.closest(".detail-button");
  if (!detailButton) {
    return;
  }
  try {
    await openSchoolDetail(detailButton.dataset.school || "");
  } catch (error) {
    showError(error);
  }
});

els.exportCsvButton.addEventListener("click", async () => {
  try {
    await exportResults("csv", false);
  } catch (error) {
    showError(error);
  }
});

els.exportExcelButton.addEventListener("click", async () => {
  try {
    await exportResults("xlsx", false);
  } catch (error) {
    showError(error);
  }
});

els.exportFavoritesCsvButton.addEventListener("click", async () => {
  try {
    await exportResults("csv", true);
  } catch (error) {
    showError(error);
  }
});

els.exportFavoritesExcelButton.addEventListener("click", async () => {
  try {
    await exportResults("xlsx", true);
  } catch (error) {
    showError(error);
  }
});

els.detailDialogClose.addEventListener("click", () => {
  els.schoolDetailDialog.close();
});

els.schoolDetailDialog.addEventListener("click", (event) => {
  if (event.target === els.schoolDetailDialog) {
    els.schoolDetailDialog.close();
  }
});

els.schoolDetailDialog.addEventListener("close", () => {
  els.statusText.textContent = state.currentPayload
    ? `已返回 ${state.currentPayload.summary.returned_group_count} 个专业组`
    : "等待检索";
});

window.addEventListener("DOMContentLoaded", async () => {
  state.apiBase = defaultApiBase();
  state.currentProvince = defaultProvince();
  els.apiBaseInput.value = state.apiBase;
  renderFavoritesPanel();
  try {
    await connectAndLoadMeta();
    await search();
  } catch (error) {
    showError(error);
  }
});
