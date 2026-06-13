# Jiangxi Pilot Notes

## Current status

Jiangxi is now build-enabled for the `2024-2025` pilot scope.

Config file:

- `F:\Pyhton_Project\China-query-of-college-admission-score\configs\provinces\jiangxi.json`

Database target:

- `F:\Pyhton_Project\China-query-of-college-admission-score\jiangxi_gaokao_admissions_2024_2025.sqlite3`

## Confirmed official sources

### 2024

- Official page:
  - `http://www.jxeea.cn/jxsjyksy/dtxx67/content/content_1856090704419688448.html`
- Official PDF:
  - `http://www.jxeea.cn/jxsjyksy/dtxx67/1856090704419688448/MNwXup7k.pdf`

### 2025

- Official page:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/content/content_1946824770752524288.html`
- Official PDF:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/1946824770752524288/6GtVOODt.pdf`

### 2023 legacy references

- First batch undergraduate official page:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/content/content_1856067033365942272.html`
- First batch undergraduate PDF:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/1856067033365942272/4h1uxe8U.pdf`
- Second batch undergraduate official page:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/content/content_1856058645798129664.html`
- Second batch undergraduate PDF:
  - `http://www.jxeea.cn/jxsjyksy/gsgg91/1856058645798129664/HYyhX7Nb.pdf`

## Confirmed gaokao.cn facts

1. Jiangxi province code is `36`.
2. Jiangxi `schoolspecialplan` API is reachable, for example:
   - `https://static-data.gaokao.cn/www/2.0/schoolspecialplan/108/2024/36.json`
   - `https://static-data.gaokao.cn/www/2.0/schoolspecialplan/108/2025/36.json`
3. Jiangxi `2024-2025` sample plan payloads confirm:
   - `local_batch_name = 本科批`
   - `type = 2073` for 物理类
   - `type = 2074` for 历史类
4. Jiangxi `2023` legacy payloads also exist, but their batch/type structure is older:
   - example: `https://static-data.gaokao.cn/www/2.0/schoolspecialplan/108/2023/36.json`

## Engineering decision

The current pilot database remains `2024-2025` on purpose.

Reason:

1. `2024-2025` official PDFs are professional-group score tables and can be matched to `gaokao.cn` major-plan data with the existing professional-group logic.
2. `2023` official PDFs are legacy school-level batch score tables (`本科一批` / `本科二批`), not `专业组` score tables.
3. So `2023` source authenticity is now confirmed, and the PDF parser can read it, but its score granularity is different from `2024-2025`.
4. Before adding `2023` into the same user-facing major recommendation flow, we should first decide how to truthfully present:
   - school-level minimum score
   - professional-group minimum score
   - real major-level minimum score

## Implementation notes

1. In this environment, Jiangxi official site requests were more stable over `http://` than `https://`.
2. `build_hunan_admissions_db.py` now includes a Jiangxi PDF parser powered by `pdfplumber`.
3. The parser handles:
   - `2024-2025` professional-group PDF tables
   - `2023` legacy batch PDF tables
4. Only `2024-2025` is enabled in province config right now.

## Frontend truthfulness strategy

1. Search, favorites, exports, and recommendation tiers remain backed only by `2024-2025` rows in `eligible_majors`.
2. The frontend now exposes a separate data-scope panel for Jiangxi:
   - current searchable years
   - current official source links
   - `2023` legacy-source warning and links
3. The school-detail dialog explicitly states that its trend chart excludes Jiangxi `2023` because those official tables are school-level batch lines rather than professional-group lines.
4. If Jiangxi `2023` is added later, it should be shipped as a separate school-line view instead of being merged into the current major-recommendation flow.
