# China Query of College Admission Score

🎓 基于各省教育考试院官方投档数据与掌上高考招生计划的多省份高考志愿检索与辅助决策系统。

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Frontend](https://img.shields.io/badge/Frontend-HTML%20%2F%20CSS%20%2F%20JavaScript-E34F26)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![Deployment](https://img.shields.io/badge/Deployed%20on-Aliyun%20ECS-FF6A00)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 📑 Table of Contents

- [Online Demo](#-online-demo)
- [What This Project Does](#-what-this-project-does)
- [Features](#-features)
- [Supported Provinces](#-supported-provinces)
- [Quick Start](#-quick-start)
- [Public Deployment](#-public-deployment)
- [How to Sync Updates to the Server](#-how-to-sync-updates-to-the-server)
- [Project Structure](#-project-structure)
- [Core Tables](#-core-tables)
- [Data Sources](#-data-sources)
- [Disclaimer](#-disclaimer)
- [Extending to More Provinces](#-extending-to-more-provinces)
- [License](#-license)

---

## ✨ Online Demo

当前已部署公网可访问版本：

- 湖南默认入口：[http://8.138.210.231:5500/?province=hunan](http://8.138.210.231:5500/?province=hunan)
- 广东入口：[http://8.138.210.231:5500/?province=guangdong](http://8.138.210.231:5500/?province=guangdong)
- 江西入口：[http://8.138.210.231:5500/?province=jiangxi](http://8.138.210.231:5500/?province=jiangxi)

> 建议直接从湖南入口进入，也可以通过页面顶部下拉框切换省份。

## 🖼️ Screenshot

![Admissions Planner Screenshot](./docs/images/app-screenshot.png)

## 🚀 What This Project Does

这是一个面向新高考省份的本地化志愿检索工具，核心流程是：

1. 自动采集各省教育考试院发布的官方本科批投档数据。
2. 交叉匹配 `gaokao.cn` 的院校招生计划与专业组信息。
3. 根据用户选科条件筛选可报专业。
4. 在浏览器中按分数检索学校、专业组与专业明细。

项目当前以 SQLite 作为数据存储，查询快、部署轻，适合本地使用和轻量公网部署。

## 🌟 Features

- 多省份配置化支持，当前已接入湖南、广东、江西。
- 基于官方投档数据构建，不依赖手工整理表格。
- 按选科规则过滤可报专业，避免无效结果。
- 提供冲、稳、保分层，便于快速筛选。
- 支持学校收藏、结果导出、学校详情与趋势查看。
- 对旧口径年份数据单独展示，避免与专业组数据混用。

## 🗂️ Supported Provinces

| 省份 | 年份范围 | 科类 / 选科 | 分数段 | 状态 |
|------|----------|-------------|--------|------|
| 湖南 | 2023-2025 | 首选物理，物化生可报 | 300-750 | 已构建 |
| 广东 | 2023-2025 | 物理类，物化生可报 | 300-750 | 已构建 |
| 江西 | 2024-2025 | 物理类，物化生可报 | 300-750 | 已构建 |

说明：

- 江西 2023 官方数据为学校级批次投档线，不是专业组口径。
- 当前江西 2023 仅作为参考信息展示，不参与专业推荐与趋势图。

## ⚡ Quick Start

### 1. Install Dependencies

如果你要本地构建数据库并运行完整流程：

```bash
pip install pandas openpyxl pdfplumber requests
```

如果你只是启动现成数据库进行查询，最小运行依赖为：

```bash
pip install openpyxl
```

### 2. Build the Database

以湖南为例：

```bash
python build_hunan_admissions_db.py --province hunan
```

广东、江西同理：

```bash
python build_hunan_admissions_db.py --province guangdong
python build_hunan_admissions_db.py --province jiangxi
```

### 3. Start the Query Server

```bash
python frontend_server.py --province hunan --port 5500
```

本地访问：

```text
http://127.0.0.1:5500/?province=hunan
```

切换省份时，修改 URL 中的 `province` 参数即可。

## ☁️ Public Deployment

项目已经验证可以直接部署到阿里云 ECS 并通过公网 IP 访问。

最简单的公网部署方案见：

- [ALIYUN_ECS_DEPLOY_SIMPLE.md](./ALIYUN_ECS_DEPLOY_SIMPLE.md)

如果你已经有数据库文件，线上运行只需要：

- `frontend_server.py`
- `province_config.py`
- `frontend/`
- `configs/`
- 对应的 `.sqlite3` 数据库文件

服务启动示例：

```bash
python frontend_server.py --province hunan --host 0.0.0.0 --port 5500
```

## 🔄 How to Sync Updates to the Server

> 本节说明：当你在本地修改了代码、 rebuilt 了数据库，或新增了省份配置后，如何把最新内容同步到阿里云 ECS。

### 1. 确认本次更新内容

本地更新通常分为三类，建议先确认你属于哪一类：

| 更新类型 | 典型场景 | 服务器端操作 |
|----------|----------|--------------|
| 代码/配置更新 | 修改了 `frontend/`、`province_config.py`、`configs/provinces/*.json` 等 | 上传覆盖 + 重启服务 |
| 数据库重建 | 本地重新运行了 `build_hunan_admissions_db.py`，生成了新的 `.sqlite3` | 上传新数据库 + 重启服务 |
| 仅前端页面调整 | 只改了 `frontend/index.html`、`app.js`、`styles.css` | 上传覆盖即可，无需重启 |

### 2. 上传文件到服务器

#### 方式 A：全量覆盖（推荐代码+配置大改时用）

如果你本地是 Windows，在本地 PowerShell 执行：

```powershell
# 1. 先把服务器上的旧目录做个备份（可选但建议）
ssh root@你的服务器公网IP "cp -r /opt/China-query-of-college-admission-score /opt/China-query-of-college-admission-score.bak.$(date +%Y%m%d)"

# 2. 上传整个项目目录
scp -r F:\Pyhton_Project\China-query-of-college-admission-score root@你的服务器公网IP:/opt/
```

> 说明：`-r` 会递归覆盖服务器上的同名文件；如果数据库文件较大，全量上传会稍慢。

#### 方式 B：仅上传变更文件（推荐小改时用）

如果你只改了个别文件，可以单独上传，避免每次都传整个目录：

```powershell
# 示例：只更新前端代码
scp F:\Pyhton_Project\China-query-of-college-admission-score\frontend\app.js root@你的服务器公网IP:/opt/China-query-of-college-admission-score/frontend/

# 示例：只更新省份配置
scp F:\Pyhton_Project\China-query-of-college-admission-score\configs\provinces\guangdong.json root@你的服务器公网IP:/opt/China-query-of-college-admission-score/configs/provinces/

# 示例：只更新数据库文件（如果本地 rebuilt 了）
scp F:\Pyhton_Project\China-query-of-college-admission-score\hunan_gaokao_admissions_2023_2025_cleaned.sqlite3 root@你的服务器公网IP:/opt/China-query-of-college-admission-score/
```

### 3. 更新服务器端依赖（如有需要）

如果本次更新引入了新的 Python 依赖，先 SSH 到服务器安装：

```bash
ssh root@你的服务器公网IP
cd /opt/China-query-of-college-admission-score
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt   # 如果有新增依赖
```

> 当前项目最小运行依赖只有 `openpyxl`，构建数据库时才需要 `pandas pdfplumber requests`。

### 4. 重启服务使更新生效

如果你使用了 [ALIYUN_ECS_DEPLOY_SIMPLE.md](./ALIYUN_ECS_DEPLOY_SIMPLE.md) 中推荐的 `systemd` 常驻方案，只需执行：

```bash
ssh root@你的服务器公网IP "systemctl restart admissions"
```

如果你是用 `screen` / `nohup` 手动跑的前台/后台进程，建议先找到进程并结束，再重新启动：

```bash
# 查找并结束旧进程
ps aux | grep frontend_server.py
kill <PID>

# 重新启动
cd /opt/China-query-of-college-admission-score
source .venv/bin/activate
python3 frontend_server.py --province hunan --host 0.0.0.0 --port 5500
```

### 5. 验证更新是否生效

重启后等待 3-5 秒，在浏览器访问公网地址确认：

```text
http://你的服务器公网IP:5500/?province=hunan
```

同时可在服务器查看服务状态与日志：

```bash
# 查看 systemd 服务状态
systemctl status admissions

# 实时查看日志
journalctl -u admissions -f
```

### 6. 高频更新建议

如果你近期频繁迭代，建议：

1. **在服务器上直接 `git pull`**（推荐）
   - 先把项目目录初始化为 Git 仓库，关联远程地址。
   - 后续更新时 SSH 到服务器执行 `git pull origin main` 即可拉取最新代码，省去 `scp` 上传步骤。
   - 数据库文件仍通过 `scp` 单独上传，或直接在服务器上运行构建脚本生成。

2. **数据库与代码分离**
   - 代码更新 → `git pull` 或 `scp` 覆盖后重启。
   - 数据库更新 → 单独 `scp` 新 `.sqlite3` 文件后重启。
   - 避免每次都全量上传包含大文件的整个目录。

---

## 🧱 Project Structure

```text
.
├── build_hunan_admissions_db.py
├── frontend_server.py
├── province_config.py
├── configs/
│   └── provinces/
├── frontend/
├── raw/
├── docs/
│   └── images/
├── queries.sql
├── JIANGXI_PILOT_NOTES.md
├── NATIONWIDE_EXPANSION_PLAN.md
├── ALIYUN_ECS_DEPLOY_SIMPLE.md
└── README.md
```

主要文件说明：

- `build_hunan_admissions_db.py`：ETL 主脚本，负责下载、解析、匹配与入库。
- `frontend_server.py`：HTTP 服务，提供页面与查询 API。
- `province_config.py`：统一读取省份配置。
- `configs/provinces/*.json`：各省份数据源、过滤规则与范围配置。
- `frontend/`：前端页面与交互逻辑。
- `docs/images/`：README 展示图片等静态资源。

## 🗃️ Core Tables

| 表名 | 说明 |
|------|------|
| `admission_groups` | 官方投档线中的院校专业组 |
| `school_mappings` | 官方院校名与 `gaokao.cn` 学校 ID 的映射 |
| `plan_major_details` | 招生计划专业明细 |
| `eligible_majors` | 选科过滤后的可报结果 |
| `unmatched_groups` | 暂未补齐专业明细的专业组 |
| `legacy_school_lines` | 旧口径年份的学校级批次投档线 |
| `sources` | 数据来源元信息 |

## 📚 Data Sources

官方投档数据来源：

- 湖南省教育考试院：`hneeb.cn` / `jyt.hunan.gov.cn`
- 广东省教育考试院：`eea.gd.gov.cn`
- 江西省教育考试院：`jxeea.cn`

招生计划数据来源：

- 掌上高考：`static-data.gaokao.cn`

## ⚠️ Disclaimer

1. 本项目仅供学习与技术交流，不构成志愿填报建议或录取承诺。
2. 当前展示的“历年分数”主要是院校专业组投档线，不等同于逐专业最低录取分。
3. 数据来自公开渠道，若官方有更新，请以各省教育考试院最新公告为准。

## 🔧 Extending to More Provinces

项目采用省份配置化设计，新增省份通常只需要：

1. 在 `configs/provinces/` 下新增对应配置文件。
2. 补充该省官方文件解析逻辑。
3. 运行构建脚本并检查匹配率与未匹配清单。

更多规划可见：

- [NATIONWIDE_EXPANSION_PLAN.md](./NATIONWIDE_EXPANSION_PLAN.md)
- [JIANGXI_PILOT_NOTES.md](./JIANGXI_PILOT_NOTES.md)

## 📄 License

MIT License
