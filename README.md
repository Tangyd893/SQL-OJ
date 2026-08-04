<p align="center">
  <img src="https://img.shields.io/badge/Tauri-2-24C8DB?style=for-the-badge&logo=tauri&logoColor=white" alt="Tauri">
  <img src="https://img.shields.io/badge/Rust-1.77+-DEA584?style=for-the-badge&logo=rust&logoColor=white" alt="Rust">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/SQLite-内存沙箱-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
</p>

<h1 align="center">🗄️ SQL OJ</h1>
<h3 align="center">桌面原生 SQL 判题系统 · Tauri + Rust</h3>
<p align="center">离线练 SQL，文件夹即题库，改文件即更新，无需 Web 后端与 Docker</p>
<p align="center">
  <b>外部题库 → 内存 SQLite 沙箱判题 → 期望/实际对比 → 练习统计</b>
</p>

---

## 💡 核心理念

> **把 OJ 从「部署一套服务」变成「打开一个桌面应用 + 选一个文件夹」**

大多数 SQL 练习环境依赖在线平台或自建 MySQL + 后端。SQL OJ 走另一条路：**题目、测试点、表结构全部是本地文件**；判题在 Rust 侧用**内存 SQLite** 执行用户 SQL，与期望结果逐行比对。没有账号系统、没有容器、没有远程数据库——适合 PTA 备考、LeetCode SQL 刷题、课堂演示与离线自学。

## 🏗️ 工作流

```
外部题库目录                    用户编写 SQL
(task.md / cases.json)              │
       │                            │
       ▼                            ▼
  ProblemBank 读取            Monaco Editor
       │                            │
       └──────────┬─────────────────┘
                  ▼
           Rust Judge（spawn_blocking）
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
  MySQL→SQLite  多测试点   10s 超时
   兼容层       逐 case 执行  1 万行上限
       │          │          │
       └──────────┴──────────┘
                  ▼
         期望结果 vs 实际结果
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
  本地提交记录            练习统计页
  (SQLite 持久化)      (日/周/月进度)
```

## 📁 项目结构

```
SQL-OJ/
├── 📖 README.md
├── 🚫 .gitignore
├── 📦 package.json                 # 前端脚本 & Tauri 命令
├── 🖥️  src/                         # React + TypeScript UI
│   ├── pages/                      #   题目列表 / 做题 / 统计 / 设置
│   ├── components/                 #   编辑器、表格、侧栏、邻题导航
│   ├── theme/tokens.css            #   明暗主题语义 token
│   └── lib/                        #   草稿、快捷键、统计聚合
├── 🦀 src-tauri/                   # Rust 后端
│   ├── src/core/
│   │   ├── bank.rs                 #   外部题库加载
│   │   ├── judge.rs                #   SQLite 内存沙箱判题
│   │   ├── mysql_compat.rs         #   MySQL → SQLite 兼容
│   │   └── storage.rs              #   设置 & 提交记录
│   └── icons/                      #   应用图标
├── 📚 sample-bank/                 # 内置 3 题示例题库（随仓库分发）
│   └── problems/p001~p003/
├── 🗃️  banks/                      # 完整题库（本地生成，默认 .gitignore）
│   └── pta-150/                    #   PTA 150 + LeetCode 275 = 425 题
└── 🐍 scripts/                     # 题库校验、导入、对齐检查
    ├── verify_bank.py
    ├── check_alignment.py
    └── import_external_problems.py
```

## 🚀 快速开始

### ✅ 前置条件

| 依赖 | 必需 | 获取方式 |
|:-----|:----:|---------|
| **Node.js 18+** | ✅ | [nodejs.org](https://nodejs.org/) |
| **Rust 1.77+** | ✅ | [rustup.rs](https://rustup.rs/) |
| **Windows 10/11** | ✅ | 当前主要目标平台（NSIS 安装包） |
| **Python 3.10+** | ⭐ | 仅维护/导入题库脚本时需要 |

> 💡 **一条命令检查：** `node --version && cargo --version`

### 📦 Step 1 — 克隆 & 安装

```bash
git clone https://github.com/Tangyd893/SQL-OJ.git
cd SQL-OJ
npm install
```

### ⚙️ Step 2 — 链接题库

首次启动后在应用内 **设置 → 选择题库目录**，或开发时直接指定：

| 题库 | 路径 | 说明 |
|:-----|:-----|:-----|
| 示例题库 | `sample-bank/` | 3 题，随仓库自带，开箱即用 |
| 完整题库 | `banks/pta-150/` | 425 题（150 PTA + 275 LeetCode），需本地生成，见下文 |

> 🤖 **让 AI 帮你：** 「帮我在 SQL-OJ 项目里运行 LeetCode 导入脚本，生成 banks/pta-150 题库」

### ▶️ Step 3 — 运行

开发模式（热更新）：

```bash
npm run tauri:dev
```

打包 Windows 安装程序：

```bash
npm run tauri:build
```

产物位于 `src-tauri/target/release/bundle/`。

便携版（免安装目录）：

```powershell
npm run tauri:build:portable
```

## ✨ 特性

### 📝 做题体验

- **Monaco SQL 编辑器**：语法高亮、多主题、草稿自动保存
- **试运行 / 提交**：试运行不写入记录；提交后持久化到本地 SQLite
- **全测试点对比**：无论 AC 或 WA，均可查看每个测试点的**期望结果**与**你的结果**
- **邻题导航**：题目页「下一题」「题目列表（±10 题）」，显示 AC 与当前题标记
- **题解页**：参考 SQL + 解析（从 `task.md` 的 `## 解析` 自动剥离）

### 📊 练习统计

- 侧栏 **练习统计** 页：环形进度（已通过 / 题库总数）
- 按 **日 / 周 / 月** 查看新通过题数与提交活跃度
- 近 26 周 GitHub 风格热力图

### 🔧 判题引擎

- 内存 SQLite 沙箱，单题 **10s 超时**、结果 **最多 1 万行**
- 拦截 `ATTACH` / `DETACH` / `PRAGMA` / `readfile()` 等危险语句
- MySQL 语法自动适配：`DATE_FORMAT`、`YEAR()`、`INSERT IGNORE`、UPDATE JOIN、`GROUP_CONCAT … SEPARATOR` 等
- 多测试点支持独立 `seed` / `schema` 覆盖

### 🎨 界面

- Fieldguide 风格布局：可拖拽分栏、可折叠侧栏
- 明暗模式 + 多套预设主题（Parchment / Slate / Midnight）
- 自定义快捷键（提交、试运行等）

## 📂 外部题库格式

```
my-bank/
├── manifest.json              # 可选，指定题目顺序与题库名称
└── problems/
    └── 0001-select-where/
        ├── meta.json          # id, title, difficulty, tags
        ├── task.md            # 题目描述（Markdown，含表结构/示例数据）
        ├── schema.sql         # 判题用建表与初始数据
        ├── cases.json         # 测试点定义
        └── solution.sql       # 可选参考题解
```

### cases.json 示例

```json
{
  "cases": [
    {
      "id": "1",
      "seed": "",
      "expected_columns": ["name", "salary"],
      "expected_rows": [["李四", 20000], ["张三", 15000]]
    }
  ]
}
```

| 字段 | 说明 |
|:-----|:-----|
| `seed` | 本测试点额外执行的 SQL（可选） |
| `schema` | 覆盖本题默认 `schema.sql`（可选） |
| `reference_sql` | 参考查询，用于推导期望或题解（可选） |

> 列名比较**不区分大小写**；行顺序**敏感**（与期望完全一致才 AC）。

### task.md 约定

| 章节 | 位置 | 说明 |
|:-----|:-----|:-----|
| `## 表结构` / 示例数据 | 题目描述页 | 题面内展示 |
| `## 目标` | 题目描述页 | 作答要求（旧版 `## 任务` 会自动转换） |
| `## 提示` | 题目描述页 | 可选提示 |
| `## 解析` | **题解页** | 加载时自动从描述中剥离 |

## 🗃️ 完整题库（425 题）

仓库内置 `sample-bank/`（3 题）。完整 **PTA SQL 150 + LeetCode 275** 题库体积较大，默认在 `.gitignore` 中，需在本地生成：

**从 MySQL 导出 PTA 150 题：**

```bash
pip install pymysql
python scripts/export_mysql_bank.py
```

**导入 LeetCode SQL 题（合并到现有 bank）：**

```bash
python scripts/import_external_problems.py --bank banks/pta-150 --workers 8
```

生成后在应用 **设置** 中链接 `banks/pta-150` 目录即可。

## 🧪 题库维护脚本

校验题库 reference 能否在 SQLite 中跑通：

```bash
npm run verify:bank
```

校验并修正 expected 数据：

```bash
npm run verify:bank:fix
```

题目 / 题解 / 测试点 全量对齐检查（425 题）：

```bash
npm run check:alignment
```

自动修复 task 标题与 solution 同步：

```bash
npm run check:alignment:fix
```

## ⌨️ 快捷键

| 操作 | 默认快捷键 |
|:-----|:-----------|
| 提交判题 | `Ctrl + Enter` |
| 试运行 | `Ctrl + Shift + Enter` |
| 切换侧栏 Tab | `Alt + 1~4` |

可在 **设置 → 快捷键** 中自定义。

## 🏛️ 架构

```
React UI  ── Tauri invoke ──▶  Rust
                               ├── ProblemBank    读取外部目录
                               ├── Judge          SQLite 内存沙箱
                               ├── mysql_compat   MySQL 方言适配
                               └── Storage        本地 sql-oj.db
                                                  （设置 + 提交记录）
```

| 层级 | 技术 |
|:-----|:-----|
| 桌面壳 | Tauri 2 |
| 前端 | React 18 + TypeScript + Vite + Monaco Editor |
| 后端 | Rust + rusqlite |
| 判题 | 内存 SQLite（非远程 MySQL） |
| 持久化 | 本地 SQLite（`app_data_dir/sql-oj.db`） |

## ❓ 常见问题

| 问题 | 解决方案 |
|:-----|---------|
| 启动后没有题目 | 进入 **设置**，链接 `sample-bank` 或本地完整题库目录 |
| 判题报 `no such function: date_format` | 题目来自 LeetCode/MySQL 源，确保使用最新版（已内置兼容层） |
| DML 题提示「未产生查询结果」 | 在 UPDATE/INSERT 后追加 `SELECT` 验证语句 |
| 修改题库后不生效 | 设置页点击 **重新加载题库**，或重启应用 |
| `banks/pta-150` 不在仓库里 | 正常，该目录被 gitignore；按上文脚本本地生成 |

## 📖 脚本参数参考

### verify_bank.py

```
python scripts/verify_bank.py --bank banks/pta-150
python scripts/verify_bank.py --bank banks/pta-150 --write-back
python scripts/verify_bank.py --bank banks/pta-150 --write-back --fix-expected
```

### check_alignment.py

```
python scripts/check_alignment.py --bank banks/pta-150
python scripts/check_alignment.py --bank banks/pta-150 --fix
```

### import_external_problems.py

```
python scripts/import_external_problems.py --bank banks/pta-150 --workers 8
python scripts/import_external_problems.py --bank banks/pta-150 --dry-run
```

---

<p align="center">
  <b>⭐ 觉得有用？点个 Star 支持一下！</b>
</p>

<p align="center">
  <a href="https://github.com/Tangyd893/SQL-OJ">github.com/Tangyd893/SQL-OJ</a>
</p>
