#!/usr/bin/env python3
"""Create interview-oriented SQL problems under banks/main and update manifest."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "banks" / "main"
PROBLEMS = BANK / "problems"

PROBLEMS.mkdir(parents=True, exist_ok=True)


def write_problem(
    slug: str,
    *,
    title: str,
    difficulty: str,
    tags: list[str],
    task: str,
    schema: str,
    solution: str,
    cases: list[dict],
    explanation: str,
) -> None:
    dest = PROBLEMS / slug
    dest.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": slug,
        "title": title,
        "difficulty": difficulty,
        "tags": tags,
    }
    (dest / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    full_task = task.rstrip() + "\n\n## 解析\n\n" + explanation.strip() + "\n"
    (dest / "task.md").write_text(full_task, encoding="utf-8")
    (dest / "schema.sql").write_text(schema.strip() + "\n", encoding="utf-8")
    (dest / "solution.sql").write_text(solution.strip() + "\n", encoding="utf-8")
    for c in cases:
        c.setdefault("reference_sql", solution.strip().rstrip(";") + ";")
        c.setdefault("seed", "")
    (dest / "cases.json").write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {slug}")


# ─── iv-001 找出重复锁号 ───────────────────────────────────────────
write_problem(
    "iv-001-dup-slots",
    title="找出重复锁号",
    difficulty="medium",
    tags=["面试", "GROUP BY", "HAVING", "防重"],
    task="""## 表结构

**registrations** 挂号记录表：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| schedule_id | INT | 排班 ID |
| slot_index | INT | 号源序号 |
| patient_id | INT | 患者 ID |

## 示例数据

| id | schedule_id | slot_index | patient_id |
|----|-------------|------------|------------|
| 1 | 10 | 1 | 1001 |
| 2 | 10 | 1 | 1002 |
| 3 | 10 | 2 | 1003 |
| 4 | 11 | 1 | 1004 |
| 5 | 11 | 1 | 1005 |
| 6 | 11 | 3 | 1006 |

## 目标

找出「同一排班 + 同一号源」被多次占用的冲突组合（一号多卖）。

要求：
- 返回 `schedule_id`, `slot_index`, `cnt`（占用次数）
- 只返回 `cnt > 1` 的行
- 按 `schedule_id`, `slot_index` 升序

## 提示

- 按 `(schedule_id, slot_index)` 分组
- 用 `HAVING COUNT(*) > 1` 过滤冲突
""",
    schema="""
DROP TABLE IF EXISTS registrations;

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);

INSERT INTO registrations (id, schedule_id, slot_index, patient_id) VALUES
(1, 10, 1, 1001),
(2, 10, 1, 1002),
(3, 10, 2, 1003),
(4, 11, 1, 1004),
(5, 11, 1, 1005),
(6, 11, 3, 1006);
""",
    solution="""
SELECT schedule_id, slot_index, COUNT(*) AS cnt
FROM registrations
GROUP BY schedule_id, slot_index
HAVING COUNT(*) > 1
ORDER BY schedule_id, slot_index;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["schedule_id", "slot_index", "cnt"],
            "expected_rows": [[10, 1, 2], [11, 1, 2]],
        },
        {
            "id": "2",
            "schema": """DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);
INSERT INTO registrations (id, schedule_id, slot_index, patient_id) VALUES
(1, 10, 1, 1001),
(2, 10, 2, 1002),
(3, 11, 1, 1003);""",
            "expected_columns": ["schedule_id", "slot_index", "cnt"],
            "expected_rows": [],
        },
    ],
    explanation="面经考点：DB 唯一索引兜底「一号多卖」。业务上应对 `(schedule_id, slot_index)` 建唯一约束；本题用聚合找出已发生的冲突行。",
)

# ─── iv-002 可挂号时段 ─────────────────────────────────────────────
write_problem(
    "iv-002-open-slots",
    title="可挂号时段",
    difficulty="medium",
    tags=["面试", "LEFT JOIN", "NOT EXISTS", "当前读"],
    task="""## 表结构

**schedules** 排班号源：

| 列名 | 类型 | 说明 |
|------|------|------|
| schedule_id | INT | 排班 ID |
| slot_index | INT | 号源序号 |
| doctor_id | INT | 医生 ID |

**registrations** 已占用号源（字段同 iv-001）。

## 示例数据

schedules:

| schedule_id | slot_index | doctor_id |
|-------------|------------|-----------|
| 10 | 1 | 1 |
| 10 | 2 | 1 |
| 10 | 3 | 1 |
| 11 | 1 | 2 |

registrations: `(10,1)` 与 `(10,2)` 已被占用。

## 目标

查询仍可挂号的号源（排班中尚未被 registration 占用的行）。

要求：
- 返回 `schedule_id`, `slot_index`, `doctor_id`
- 按 `schedule_id`, `slot_index` 升序

## 提示

- `LEFT JOIN ... WHERE r.id IS NULL`，或 `NOT EXISTS`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS schedules;

CREATE TABLE schedules (
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  doctor_id INTEGER NOT NULL
);

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);

INSERT INTO schedules (schedule_id, slot_index, doctor_id) VALUES
(10, 1, 1),
(10, 2, 1),
(10, 3, 1),
(11, 1, 2);

INSERT INTO registrations (id, schedule_id, slot_index, patient_id) VALUES
(1, 10, 1, 1001),
(2, 10, 2, 1002);
""",
    solution="""
SELECT s.schedule_id, s.slot_index, s.doctor_id
FROM schedules s
LEFT JOIN registrations r
  ON s.schedule_id = r.schedule_id AND s.slot_index = r.slot_index
WHERE r.id IS NULL
ORDER BY s.schedule_id, s.slot_index;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["schedule_id", "slot_index", "doctor_id"],
            "expected_rows": [[10, 3, 1], [11, 1, 2]],
        }
    ],
    explanation="面经考点：SELECT FOR UPDATE 前先定位「待锁行」。本题练习找出仍可占用的号源；线上再对这些行做当前读加锁。",
)

# ─── iv-003 范围代替函数过滤日期 ───────────────────────────────────
write_problem(
    "iv-003-date-range",
    title="用范围代替函数过滤日期",
    difficulty="easy",
    tags=["面试", "日期", "索引友好", "范围查询"],
    task="""## 表结构

**orders** 订单表：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| created_at | TEXT | 下单时间，格式 `YYYY-MM-DD HH:MM:SS` |
| amount | INT | 金额 |

## 示例数据

含 2025 与 2026 年订单若干。

## 目标

查询 **2026 年** 的全部订单。

要求：
- 返回 `id`, `created_at`, `amount`
- 按 `id` 升序
- **不要**对 `created_at` 使用 `YEAR()` / `strftime('%Y', ...)` 等函数包裹（面试强调索引失效）

## 提示

- 写成半开区间：`created_at >= '2026-01-01' AND created_at < '2027-01-01'`
""",
    schema="""
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  amount INTEGER NOT NULL
);

INSERT INTO orders (id, created_at, amount) VALUES
(1, '2025-12-31 23:00:00', 10),
(2, '2026-01-01 00:00:00', 20),
(3, '2026-06-15 12:00:00', 30),
(4, '2026-12-31 23:59:59', 40),
(5, '2027-01-01 00:00:00', 50);
""",
    solution="""
SELECT id, created_at, amount
FROM orders
WHERE created_at >= '2026-01-01'
  AND created_at < '2027-01-01'
ORDER BY id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["id", "created_at", "amount"],
            "expected_rows": [
                [2, "2026-01-01 00:00:00", 20],
                [3, "2026-06-15 12:00:00", 30],
                [4, "2026-12-31 23:59:59", 40],
            ],
        }
    ],
    explanation="面经考点：函数作用于索引列会导致索引失效。用范围条件保留对 `created_at` 的索引可用性。",
)

# ─── iv-004 OR 改 UNION ────────────────────────────────────────────
write_problem(
    "iv-004-or-to-union",
    title="OR 条件改 UNION",
    difficulty="medium",
    tags=["面试", "UNION", "OR", "索引友好"],
    task="""## 表结构

**tickets** 工单：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| dept_a | INT | 是否 A 部门相关（1/0） |
| dept_c | INT | 是否 C 部门相关（1/0） |
| title | TEXT | 标题 |

说明：模拟 `WHERE a=1 OR c=1` 场景（`dept_a=1` 或 `dept_c=1`）。

## 目标

查出与 A 部门或 C 部门相关的工单（去重）。

要求：
- 返回 `id`, `title`
- 按 `id` 升序
- 推荐用 **`UNION`**（而非单一 `OR`）表达，便于两边各走索引

## 提示

- `SELECT ... WHERE dept_a = 1 UNION SELECT ... WHERE dept_c = 1`
- `UNION` 默认去重；若确定无交集可用 `UNION ALL` 再外包去重，本题用 `UNION` 即可
""",
    schema="""
DROP TABLE IF EXISTS tickets;

CREATE TABLE tickets (
  id INTEGER PRIMARY KEY,
  dept_a INTEGER NOT NULL,
  dept_c INTEGER NOT NULL,
  title TEXT NOT NULL
);

INSERT INTO tickets (id, dept_a, dept_c, title) VALUES
(1, 1, 0, 'A only'),
(2, 0, 1, 'C only'),
(3, 1, 1, 'Both'),
(4, 0, 0, 'Neither');
""",
    solution="""
SELECT id, title FROM tickets WHERE dept_a = 1
UNION
SELECT id, title FROM tickets WHERE dept_c = 1
ORDER BY id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["id", "title"],
            "expected_rows": [
                [1, "A only"],
                [2, "C only"],
                [3, "Both"],
            ],
        }
    ],
    explanation="面经考点：`OR` 常使优化器放弃联合索引。拆成 `UNION` 后两边可各走 `INDEX(a)` / `INDEX(c)`。",
)

# ─── iv-005 等值联合筛选 ───────────────────────────────────────────
write_problem(
    "iv-005-eq-composite",
    title="等值条件联合筛选",
    difficulty="easy",
    tags=["面试", "多条件", "联合索引"],
    task="""## 表结构

**events** 事件表：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| a | INT | 维度 A |
| b | INT | 维度 B（不等条件用） |
| c | INT | 维度 C |
| name | TEXT | 名称 |

## 目标

筛选 `a = 1` 且 `c = 1` 的事件（面试题里 `b <> 1` 不走索引，本题只练等值列）。

要求：
- 返回 `id`, `name`
- 按 `id` 升序

## 提示

- `WHERE a = 1 AND c = 1`，联合索引应建在等值列 `(a, c)` 上
""",
    schema="""
DROP TABLE IF EXISTS events;

CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  a INTEGER NOT NULL,
  b INTEGER NOT NULL,
  c INTEGER NOT NULL,
  name TEXT NOT NULL
);

INSERT INTO events (id, a, b, c, name) VALUES
(1, 1, 0, 1, 'hit'),
(2, 1, 2, 0, 'no-c'),
(3, 0, 0, 1, 'no-a'),
(4, 1, 9, 1, 'hit2'),
(5, 1, 1, 1, 'hit3');
""",
    solution="""
SELECT id, name
FROM events
WHERE a = 1 AND c = 1
ORDER BY id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["id", "name"],
            "expected_rows": [[1, "hit"], [4, "hit2"], [5, "hit3"]],
        }
    ],
    explanation="面经考点：`WHERE a=1 AND b<>1 AND c=1` 时 `<>` 不走索引，联合索引应放在等值列 `(a,c)`。",
)

# ─── iv-006 科室挂号量 Top-N ────────────────────────────────────────
write_problem(
    "iv-006-dept-topn",
    title="科室挂号量排行 Top-N",
    difficulty="medium",
    tags=["面试", "GROUP BY", "ORDER BY", "LIMIT", "排行榜"],
    task="""## 表结构

**registrations**：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| dept_id | INT | 科室 ID |
| patient_id | INT | 患者 |

**depts**：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 科室 ID |
| name | TEXT | 科室名 |

## 目标

统计各科室挂号量，取 **Top 3**。

要求：
- 返回 `dept_id`, `name`, `cnt`
- 按 `cnt` 降序，`dept_id` 升序
- 只返回前 3 行

## 提示

- `JOIN` + `GROUP BY` + `ORDER BY cnt DESC` + `LIMIT 3`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS depts;

CREATE TABLE depts (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  dept_id INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);

INSERT INTO depts (id, name) VALUES
(1, '内科'),
(2, '外科'),
(3, '儿科'),
(4, '骨科');

INSERT INTO registrations (id, dept_id, patient_id) VALUES
(1, 1, 1), (2, 1, 2), (3, 1, 3), (4, 1, 4),
(5, 2, 5), (6, 2, 6), (7, 2, 7),
(8, 3, 8), (9, 3, 9),
(10, 4, 10);
""",
    solution="""
SELECT d.id AS dept_id, d.name, COUNT(*) AS cnt
FROM depts d
JOIN registrations r ON d.id = r.dept_id
GROUP BY d.id, d.name
ORDER BY cnt DESC, d.id
LIMIT 3;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["dept_id", "name", "cnt"],
            "expected_rows": [
                [1, "内科", 4],
                [2, "外科", 3],
                [3, "儿科", 2],
            ],
        }
    ],
    explanation="面经考点：Redis ZSet 排行榜在 SQL 侧的对应写法——聚合后排序取 Top-N。",
)

# ─── iv-007 近 N 日滑动窗口 ────────────────────────────────────────
write_problem(
    "iv-007-sliding-window",
    title="近 N 日滑动窗口统计",
    difficulty="medium",
    tags=["面试", "日期", "聚合", "滑动窗口"],
    task="""## 表结构

**requests** 请求日志：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户 |
| req_at | TEXT | 请求时间 `YYYY-MM-DD HH:MM:SS` |

基准时刻视为 **`2026-07-01 12:00:00`**，统计该时刻往前 **24 小时内**（半开区间）的请求数，按用户汇总。

## 目标

返回在窗口内有请求的用户及其次数。

要求：
- 返回 `user_id`, `cnt`
- 窗口：`req_at >= '2026-06-30 12:00:00' AND req_at < '2026-07-01 12:00:00'`
- 按 `user_id` 升序

## 提示

- 类似 Redis ZSet 滑动窗口：删掉窗口外的点再计数
""",
    schema="""
DROP TABLE IF EXISTS requests;

CREATE TABLE requests (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  req_at TEXT NOT NULL
);

INSERT INTO requests (id, user_id, req_at) VALUES
(1, 1, '2026-06-30 11:59:59'),
(2, 1, '2026-06-30 12:00:00'),
(3, 1, '2026-07-01 11:59:59'),
(4, 1, '2026-07-01 12:00:00'),
(5, 2, '2026-06-30 15:00:00'),
(6, 2, '2026-07-01 10:00:00'),
(7, 3, '2026-06-29 12:00:00');
""",
    solution="""
SELECT user_id, COUNT(*) AS cnt
FROM requests
WHERE req_at >= '2026-06-30 12:00:00'
  AND req_at < '2026-07-01 12:00:00'
GROUP BY user_id
ORDER BY user_id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["user_id", "cnt"],
            "expected_rows": [[1, 2], [2, 2]],
        }
    ],
    explanation="面经考点：滑动窗口限流（ZREMRANGEBYSCORE + ZCARD）在 SQL 中用时间范围聚合表达。",
)

# ─── iv-008 子查询改 JOIN ───────────────────────────────────────────
write_problem(
    "iv-008-join-agg",
    title="子查询改 JOIN 统计",
    difficulty="medium",
    tags=["面试", "JOIN", "GROUP BY", "慢查询"],
    task="""## 表结构

**doctors** / **registrations**（registrations.doctor_id → doctors.id）

## 目标

列出每位医生的姓名及其挂号量 `cnt`（没有挂号则为 0）。

要求：
- 返回 `doctor_id`, `name`, `cnt`
- 按 `doctor_id` 升序
- 用 **JOIN（或 LEFT JOIN）聚合**，避免相关子查询逐行计算

## 提示

- `LEFT JOIN` + `GROUP BY` + `COUNT(r.id)`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS doctors;

CREATE TABLE doctors (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);

INSERT INTO doctors (id, name) VALUES
(1, '张医生'),
(2, '李医生'),
(3, '王医生');

INSERT INTO registrations (id, doctor_id, patient_id) VALUES
(1, 1, 10),
(2, 1, 11),
(3, 2, 12);
""",
    solution="""
SELECT d.id AS doctor_id, d.name, COUNT(r.id) AS cnt
FROM doctors d
LEFT JOIN registrations r ON d.id = r.doctor_id
GROUP BY d.id, d.name
ORDER BY d.id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["doctor_id", "name", "cnt"],
            "expected_rows": [
                [1, "张医生", 2],
                [2, "李医生", 1],
                [3, "王医生", 0],
            ],
        }
    ],
    explanation="面经考点：慢查询优化时常把相关子查询改为 JOIN 一次聚合。",
)

# ─── iv-009 只查需要的列 ───────────────────────────────────────────
write_problem(
    "iv-009-select-cols",
    title="只查询需要的列",
    difficulty="easy",
    tags=["面试", "SELECT", "覆盖索引"],
    task="""## 表结构

**patients** 患者：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| name | TEXT | 姓名 |
| phone | TEXT | 手机 |
| id_card | TEXT | 身份证 |
| address | TEXT | 地址 |
| remark | TEXT | 备注 |

## 目标

导出用于短信通知的名单：仅需 `id`, `name`, `phone`，且 `phone` 非空。

要求：
- 返回三列，按 `id` 升序
- **不要** `SELECT *`

## 提示

- 明确列出列名，利于覆盖索引与减少 IO
""",
    schema="""
DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT,
  id_card TEXT,
  address TEXT,
  remark TEXT
);

INSERT INTO patients (id, name, phone, id_card, address, remark) VALUES
(1, '甲', '13800000001', 'x', 'addr1', 'r1'),
(2, '乙', NULL, 'y', 'addr2', 'r2'),
(3, '丙', '13800000003', 'z', 'addr3', 'r3');
""",
    solution="""
SELECT id, name, phone
FROM patients
WHERE phone IS NOT NULL
ORDER BY id;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["id", "name", "phone"],
            "expected_rows": [
                [1, "甲", "13800000001"],
                [3, "丙", "13800000003"],
            ],
        }
    ],
    explanation="面经考点：避免 `SELECT *`，只取业务需要的列，便于覆盖索引与降低回表成本。",
)

# ─── iv-010 冲突预约对 ─────────────────────────────────────────────
write_problem(
    "iv-010-conflict-pairs",
    title="查出冲突预约对",
    difficulty="hard",
    tags=["面试", "自连接", "并发冲突"],
    task="""## 表结构

**registrations**：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| schedule_id | INT | 排班 |
| slot_index | INT | 号源 |
| patient_id | INT | 患者 |
| created_at | TEXT | 创建时间 |

## 目标

列出所有「抢到同一号源」的冲突患者对。

要求：
- 返回 `schedule_id`, `slot_index`, `patient_a`, `patient_b`
- 同一冲突只输出一次，且 `patient_a < patient_b`
- 按 `schedule_id`, `slot_index`, `patient_a`, `patient_b` 升序

## 提示

- 自连接：`r1.schedule_id = r2.schedule_id AND r1.slot_index = r2.slot_index AND r1.patient_id < r2.patient_id`
""",
    schema="""
DROP TABLE IF EXISTS registrations;

CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  patient_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO registrations (id, schedule_id, slot_index, patient_id, created_at) VALUES
(1, 10, 1, 100, '2026-07-01 10:00:00'),
(2, 10, 1, 200, '2026-07-01 10:00:01'),
(3, 10, 1, 300, '2026-07-01 10:00:02'),
(4, 10, 2, 100, '2026-07-01 10:01:00'),
(5, 11, 1, 400, '2026-07-01 10:02:00'),
(6, 11, 1, 500, '2026-07-01 10:02:01');
""",
    solution="""
SELECT r1.schedule_id, r1.slot_index,
       r1.patient_id AS patient_a,
       r2.patient_id AS patient_b
FROM registrations r1
JOIN registrations r2
  ON r1.schedule_id = r2.schedule_id
 AND r1.slot_index = r2.slot_index
 AND r1.patient_id < r2.patient_id
ORDER BY r1.schedule_id, r1.slot_index, patient_a, patient_b;
""",
    cases=[
        {
            "id": "1",
            "expected_columns": ["schedule_id", "slot_index", "patient_a", "patient_b"],
            "expected_rows": [
                [10, 1, 100, 200],
                [10, 1, 100, 300],
                [10, 1, 200, 300],
                [11, 1, 400, 500],
            ],
        }
    ],
    explanation="面经考点：高并发下用自连接审计已发生的冲突预约对，对应「防一号多卖」事后排查。",
)


def update_manifest() -> None:
    manifest_path = BANK / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["name"] = "SQL OJ Main"
    data["version"] = "1.1.0"
    data["source"] = "pta+leetcode+interview"
    iv = sorted(
        p.name
        for p in PROBLEMS.iterdir()
        if p.is_dir() and p.name.startswith("iv-")
    )
    existing = [x for x in data.get("problems", []) if not str(x).startswith("iv-")]
    data["problems"] = existing + iv
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest problems={len(data['problems'])} (iv={len(iv)})")


if __name__ == "__main__":
    update_manifest()
