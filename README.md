# China Query of College Admission Score

> 基于各省教育考试院官方投档数据与掌上高考招生计划的多省份高考志愿检索与辅助决策系统。

---

## 项目简介

本项目是一套面向新高考省份的**本地化高考志愿检索工具**。核心流程为：

1. **自动采集**各省教育考试院发布的官方本科批投档线（PDF / Excel / ZIP）。
2. **交叉匹配**`gaokao.cn`（掌上高考）公布的院校招生计划与专业组信息。
3. **按选科过滤**根据用户画像（如物理+化学+生物）筛选可报考专业。
4. **本地查询**通过浏览器前端按分数检索，提供冲/稳/保分层、学校收藏、趋势分析与导出功能。

所有数据落地在本地 SQLite，无需依赖第三方云服务，保证隐私与查询速度。

---

## 功能特性

- **多省份配置化支持**：湖南、广东、江西已接入，通过 `configs/provinces/*.json` 即可新增省份。
- **官方数据源直连**：自动下载各省教育考试院原始文件，保留完整来源可追溯。
- **选科-aware 过滤**：根据考生选科组合，按专业组选科要求精确筛选可报专业。
- **冲稳保智能分层**：基于历史专业组投档线与考生预估分的分差自动分级。
- **学校收藏与导出**：支持收藏意向学校，并导出当前结果或收藏列表为 CSV / Excel。
- **学校详情与趋势图**：查看某所学校历年专业组投档线变化，辅助判断填报策略。
- ** legacy 数据兼容**：对旧高考年份的学校级批次线单独展示，避免与专业组数据混用。

---

## 已支持省份与数据范围

| 省份 | 年份范围 | 科类/选科 | 分数段 | 数据状态 |
|------|----------|-----------|--------|----------|
| 湖南 | 2023–2025 | 首选物理（物化生可报） | 300–750 | 已构建 |
| 广东 | 2023–2025 | 物理类（物化生可报） | 300–750 | 已构建 |
| 江西 | 2024–2025 | 物理类（物化生可报） | 300–750 | 已构建 |

> 注：江西 2023 年官方数据为学校级批次投档线（非专业组口径），当前作为参考数据单独展示，不混入专业推荐与趋势图。

---

## 技术栈

- **Python 3.11+**
  - `pandas` / `openpyxl`：Excel 解析与数据处理
  - `pdfplumber`：PDF 表格抽取（江西、广东官方投档表）
  - `requests`：官方文件与招生计划下载
  - `sqlite3`：本地数据持久化
- **前端**
  - 原生 HTML5 / CSS3 / JavaScript（无框架依赖）
  - SVG 自绘制趋势图
- **架构**
  - 配置驱动的 ETL：`configs/provinces/*.json` 定义省份代码、数据源、过滤规则
  - 共享配置层：`province_config.py` 统一向后端构建脚本与前端服务暴露省份信息

---

## 快速开始

### 1. 克隆仓库并安装依赖

```bash
cd China-query-of-college-admission-score
pip install pandas openpyxl pdfplumber requests
```

### 2. 构建省份数据库

以湖南为例：

```bash
python build_hunan_admissions_db.py --province hunan
```

构建完成后，会在项目根目录生成：

```
hunan_gaokao_admissions_2023_2025_cleaned.sqlite3
```

同理可构建广东、江西：

```bash
python build_hunan_admissions_db.py --province guangdong
python build_hunan_admissions_db.py --province jiangxi
```

### 3. 启动前端查询服务

```bash
python frontend_server.py --province hunan --port 5500
```

在浏览器打开：

```
http://127.0.0.1:5500/?province=hunan
```

切换省份时，修改 URL 参数 `province=guangdong` 或 `jiangxi`，或直接在页面顶部下拉框切换。

---

## 项目结构

```
.
├── build_hunan_admissions_db.py   # ETL 主脚本：下载、解析、匹配、入库
├── frontend_server.py             # 本地 HTTP 服务，提供 API 与静态页面
├── province_config.py             # 省份配置读取与共享工具
├── configs/
│   └── provinces/
│       ├── hunan.json             # 湖南省配置（数据源、过滤规则、分数段）
│       ├── guangdong.json         # 广东省配置
│       └── jiangxi.json         # 江西省配置
├── frontend/
│   ├── index.html                 # 检索页面
│   ├── app.js                     # 前端逻辑（检索、收藏、导出、趋势图）
│   └── styles.css                 # 样式
├── raw/                           # 原始官方文件（运行时自动下载，默认不提交 Git）
├── queries.sql                    # 常用审计与抽样查询 SQL
├── NATIONWIDE_EXPANSION_PLAN.md   # 全国化扩容计划文档
├── JIANGXI_PILOT_NOTES.md         # 江西试点技术备忘
└── README.md
```

---

## 核心数据表说明

| 表名 | 说明 |
|------|------|
| `admission_groups` | 官方投档线中的院校专业组 |
| `school_mappings` | 官方院校名 ↔ `gaokao.cn` 学校 ID 的映射关系 |
| `plan_major_details` | 从 `gaokao.cn` 抓取的省份招生计划明细 |
| `eligible_majors` | 按考生选科筛选后可报的学校-专业结果 |
| `unmatched_groups` | 未能补齐专业明细的专业组，用于人工复核 |
| `legacy_school_lines` | 旧高考年份的学校级批次投档线 |
| `sources` | 所有数据来源的元信息（URL、文件路径、抓取时间） |

---

## 数据来源与声明

### 官方投档数据

- **湖南省教育考试院**：`hneeb.cn` / `jyt.hunan.gov.cn`
- **广东省教育考试院**：`eea.gd.gov.cn`
- **江西省教育考试院**：`jxeea.cn`

### 招生计划数据

- **掌上高考（`gaokao.cn`）**：`static-data.gaokao.cn`

### 重要声明

1. **本项目仅供学习与技术交流**，不构成任何志愿填报建议或录取承诺。
2. 当前数据库展示的“历年分数”主要是**院校专业组投档线**，不是**逐专业最低录取分**。页面已做明确提示，请用户知悉。
3. 数据均来自公开官方渠道，如有更新请以各省教育考试院最新公告为准。

---

## 扩展路线

项目设计为“省份配置化”框架，新增省份通常只需：

1. 在 `configs/provinces/` 下新增 `{province}.json`，填写：
   - 省份代码与名称
   - 官方数据源 URL 与文件格式
   - 分数段与科类过滤规则
   - `gaokao.cn` 对应的省份代码
2. 若官方文件为 PDF，在 `build_hunan_admissions_db.py` 中补充对应解析器。
3. 运行构建脚本并验证映射率与未匹配清单。

更详细的阶段规划见 [NATIONWIDE_EXPANSION_PLAN.md](./NATIONWIDE_EXPANSION_PLAN.md)。

---

## License

MIT License

---

## 致谢

- 各省教育考试院公开数据
- 掌上高考（`gaokao.cn`）静态招生计划接口
