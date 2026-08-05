#!/usr/bin/env python3
"""Expand interview SQL set: iv-011 … iv-030 under banks/main."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "banks" / "main"
PROBLEMS = BANK / "problems"


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
    sol = solution.strip().rstrip(";") + ";"
    for c in cases:
        c.setdefault("reference_sql", sol)
        c.setdefault("seed", "")
    (dest / "cases.json").write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {slug}")


write_problem(
    "iv-011-interval-overlap",
    title="预约时间段重叠",
    difficulty="hard",
    tags=["面试", "自连接", "区间重叠", "并发冲突"],
    task="""## 表结构

**appointments** 预约：

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| room_id | INT | 诊室 |
| start_at | TEXT | 开始 `YYYY-MM-DD HH:MM:SS` |
| end_at | TEXT | 结束（半开：不含终点） |
| patient_id | INT | 患者 |

## 目标

找出同一诊室时间段重叠的预约对。

要求：
- 返回 `room_id`, `id_a`, `id_b`（`id_a < id_b`）
- 重叠判定：`a.start < b.end AND b.start < a.end`
- 按 `room_id`, `id_a`, `id_b` 升序

## 提示

- 自连接 + 区间相交条件；排除自己与自己
""",
    schema="""
DROP TABLE IF EXISTS appointments;
CREATE TABLE appointments (
  id INTEGER PRIMARY KEY,
  room_id INTEGER NOT NULL,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  patient_id INTEGER NOT NULL
);
INSERT INTO appointments (id, room_id, start_at, end_at, patient_id) VALUES
(1, 1, '2026-07-01 09:00:00', '2026-07-01 10:00:00', 100),
(2, 1, '2026-07-01 09:30:00', '2026-07-01 10:30:00', 101),
(3, 1, '2026-07-01 10:00:00', '2026-07-01 11:00:00', 102),
(4, 2, '2026-07-01 09:00:00', '2026-07-01 10:00:00', 103),
(5, 2, '2026-07-01 10:00:00', '2026-07-01 11:00:00', 104);
""",
    solution="""
SELECT a.room_id, a.id AS id_a, b.id AS id_b
FROM appointments a
JOIN appointments b
  ON a.room_id = b.room_id
 AND a.id < b.id
 AND a.start_at < b.end_at
 AND b.start_at < a.end_at
ORDER BY a.room_id, id_a, id_b;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["room_id", "id_a", "id_b"],
        "expected_rows": [[1, 1, 2], [1, 2, 3]],
    }],
    explanation="面经并发冲突延伸：不仅号源重复，时段重叠也会冲突。半开区间下 id=1 与 id=3 在 10:00 相接不相交；id=2 与两者皆重叠。",
)

write_problem(
    "iv-012-keyset-page",
    title="键集分页代替大 OFFSET",
    difficulty="medium",
    tags=["面试", "分页", "ORDER BY", "慢查询"],
    task="""## 表结构

**registrations**：`id` 主键自增，`created_at` 创建时间，`patient_id` 患者。

上一页最后一条为 `id = 3`。请取 **之后** 的下一页 2 条（按 `id` 升序）。

## 目标

返回 `id`, `patient_id`, `created_at`，共至多 2 行。

## 提示

- 慢查询常因 `LIMIT 100000, 10` 深分页；改用 `WHERE id > ? ORDER BY id LIMIT n`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  patient_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO registrations (id, patient_id, created_at) VALUES
(1, 10, '2026-07-01 09:00:00'),
(2, 11, '2026-07-01 09:01:00'),
(3, 12, '2026-07-01 09:02:00'),
(4, 13, '2026-07-01 09:03:00'),
(5, 14, '2026-07-01 09:04:00'),
(6, 15, '2026-07-01 09:05:00');
""",
    solution="""
SELECT id, patient_id, created_at
FROM registrations
WHERE id > 3
ORDER BY id
LIMIT 2;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "patient_id", "created_at"],
        "expected_rows": [
            [4, 13, "2026-07-01 09:03:00"],
            [5, 14, "2026-07-01 09:04:00"],
        ],
    }],
    explanation="面经慢查询：深 OFFSET 扫描浪费。键集分页用上次最大 id 定位，稳定且可走主键。",
)

write_problem(
    "iv-013-exists-active-doctors",
    title="EXISTS 找出有挂号的医生",
    difficulty="medium",
    tags=["面试", "EXISTS", "半连接"],
    task="""## 表结构

**doctors** / **registrations**（`registrations.doctor_id`）

## 目标

列出至少有一条挂号记录的医生。

要求：
- 返回 `id`, `name`
- 按 `id` 升序
- 使用 `EXISTS`（不要用 `IN (SELECT ...)` 完成本题）

## 提示

- `WHERE EXISTS (SELECT 1 FROM registrations r WHERE r.doctor_id = d.id)`
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
(1, '张医生'), (2, '李医生'), (3, '王医生');
INSERT INTO registrations (id, doctor_id, patient_id) VALUES
(1, 1, 10), (2, 1, 11), (3, 3, 12);
""",
    solution="""
SELECT d.id, d.name
FROM doctors d
WHERE EXISTS (
  SELECT 1 FROM registrations r WHERE r.doctor_id = d.id
)
ORDER BY d.id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "name"],
        "expected_rows": [[1, "张医生"], [3, "王医生"]],
    }],
    explanation="面经半连接：`EXISTS` 找到一条即可短路，常比 `IN` + 去重更清晰，也利于优化器。",
)

write_problem(
    "iv-014-not-exists-patients",
    title="从未挂号的患者",
    difficulty="medium",
    tags=["面试", "NOT EXISTS", "反连接"],
    task="""## 表结构

**patients** / **registrations**（`registrations.patient_id`）

## 目标

找出从未产生挂号记录的患者。

要求：
- 返回 `id`, `name`
- 按 `id` 升序
- 使用 `NOT EXISTS`

## 提示

- 反连接：患者侧不存在对应 registration
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS patients;
CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  patient_id INTEGER NOT NULL,
  dept_id INTEGER NOT NULL
);
INSERT INTO patients (id, name) VALUES
(1, '甲'), (2, '乙'), (3, '丙'), (4, '丁');
INSERT INTO registrations (id, patient_id, dept_id) VALUES
(1, 1, 10), (2, 3, 11), (3, 1, 12);
""",
    solution="""
SELECT p.id, p.name
FROM patients p
WHERE NOT EXISTS (
  SELECT 1 FROM registrations r WHERE r.patient_id = p.id
)
ORDER BY p.id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "name"],
        "expected_rows": [[2, "乙"], [4, "丁"]],
    }],
    explanation="面经反连接：`NOT EXISTS` 表达「无关联行」，注意 `NOT IN` 遇 NULL 的陷阱，优先 EXISTS。",
)

write_problem(
    "iv-015-latest-per-doctor",
    title="每位医生最近一次挂号",
    difficulty="hard",
    tags=["面试", "分组最大", "JOIN", "窗口替代"],
    task="""## 表结构

**registrations**：`id`, `doctor_id`, `patient_id`, `created_at`

## 目标

每位医生只保留 **最近一次** 挂号（`created_at` 最大；若并列取 `id` 最大）。

要求：
- 返回 `doctor_id`, `patient_id`, `created_at`
- 按 `doctor_id` 升序

## 提示

- 先按医生求 `MAX(created_at)`，再回表关联；并列时再用 `id` 决胜
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER NOT NULL,
  patient_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO registrations (id, doctor_id, patient_id, created_at) VALUES
(1, 1, 10, '2026-07-01 09:00:00'),
(2, 1, 11, '2026-07-01 10:00:00'),
(3, 1, 12, '2026-07-01 10:00:00'),
(4, 2, 20, '2026-07-01 08:00:00'),
(5, 2, 21, '2026-07-01 11:00:00'),
(6, 3, 30, '2026-07-01 12:00:00');
""",
    solution="""
SELECT r.doctor_id, r.patient_id, r.created_at
FROM registrations r
JOIN (
  SELECT doctor_id, MAX(created_at) AS max_at
  FROM registrations
  GROUP BY doctor_id
) t ON r.doctor_id = t.doctor_id AND r.created_at = t.max_at
JOIN (
  SELECT doctor_id, created_at, MAX(id) AS max_id
  FROM registrations
  GROUP BY doctor_id, created_at
) u ON r.doctor_id = u.doctor_id
   AND r.created_at = u.created_at
   AND r.id = u.max_id
ORDER BY r.doctor_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["doctor_id", "patient_id", "created_at"],
        "expected_rows": [
            [1, 12, "2026-07-01 10:00:00"],
            [2, 21, "2026-07-01 11:00:00"],
            [3, 30, "2026-07-01 12:00:00"],
        ],
    }],
    explanation="面经「每组取最新」：无窗口函数时用分组最大值回表；时间并列用主键决胜，避免重复行。",
)

write_problem(
    "iv-016-case-status-agg",
    title="按状态条件聚合",
    difficulty="medium",
    tags=["面试", "CASE", "条件聚合", "GROUP BY"],
    task="""## 表结构

**registrations**：`dept_id`, `status`（`ok` / `cancel` / `timeout`）

## 目标

按科室统计成功数、取消数、超时数。

要求：
- 返回 `dept_id`, `ok_cnt`, `cancel_cnt`, `timeout_cnt`
- 按 `dept_id` 升序

## 提示

- `SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END)`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  dept_id INTEGER NOT NULL,
  status TEXT NOT NULL
);
INSERT INTO registrations (id, dept_id, status) VALUES
(1, 1, 'ok'), (2, 1, 'ok'), (3, 1, 'cancel'),
(4, 2, 'timeout'), (5, 2, 'ok'), (6, 2, 'cancel'), (7, 2, 'cancel'),
(8, 3, 'ok');
""",
    solution="""
SELECT dept_id,
       SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS ok_cnt,
       SUM(CASE WHEN status = 'cancel' THEN 1 ELSE 0 END) AS cancel_cnt,
       SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) AS timeout_cnt
FROM registrations
GROUP BY dept_id
ORDER BY dept_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["dept_id", "ok_cnt", "cancel_cnt", "timeout_cnt"],
        "expected_rows": [
            [1, 2, 1, 0],
            [2, 1, 2, 1],
            [3, 1, 0, 0],
        ],
    }],
    explanation="面经报表/慢查询：一次扫描用 CASE 条件聚合，避免多次子查询扫表。",
)

write_problem(
    "iv-017-varchar-compare",
    title="字符串列用字符比较",
    difficulty="easy",
    tags=["面试", "类型", "索引失效", "隐式转换"],
    task="""## 表结构

**users**：`id`, `uid`（业务号，**TEXT** 存储，可能含前导零）

## 目标

查询 `uid = '00128'` 的用户（必须按字符串精确匹配）。

要求：
- 返回 `id`, `uid`, `name`
- 按 `id` 升序

## 提示

- 面经：`WHERE varchar_col = 128` 会隐式转换导致索引失效/错匹配；请写 `uid = '00128'`
""",
    schema="""
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  uid TEXT NOT NULL,
  name TEXT NOT NULL
);
INSERT INTO users (id, uid, name) VALUES
(1, '00128', '甲'),
(2, '128', '乙'),
(3, '00129', '丙');
""",
    solution="""
SELECT id, uid, name
FROM users
WHERE uid = '00128'
ORDER BY id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "uid", "name"],
        "expected_rows": [[1, "00128", "甲"]],
    }],
    explanation="面经索引失效：字符串列与数字比较会隐式转换。业务号、订单号一律按字符串字面量比较。",
)

write_problem(
    "iv-018-prefix-like",
    title="前缀模糊查询",
    difficulty="easy",
    tags=["面试", "LIKE", "索引友好"],
    task="""## 表结构

**doctors**：`id`, `code`（工号 TEXT）, `name`

## 目标

查询工号以 `D10` 开头的医生。

要求：
- 返回 `id`, `code`, `name`
- 按 `code` 升序
- 使用前缀模式 `LIKE 'D10%'`（不要写成 `'%D10'`）

## 提示

- 前缀 LIKE 才可能走索引；前导 `%` 通常无法用 BTree 索引
""",
    schema="""
DROP TABLE IF EXISTS doctors;
CREATE TABLE doctors (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL,
  name TEXT NOT NULL
);
INSERT INTO doctors (id, code, name) VALUES
(1, 'D1001', '张'),
(2, 'D1002', '李'),
(3, 'D2001', '王'),
(4, 'X1001', '赵'),
(5, 'D10', '钱');
""",
    solution="""
SELECT id, code, name
FROM doctors
WHERE code LIKE 'D10%'
ORDER BY code;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "code", "name"],
        "expected_rows": [
            [5, "D10", "钱"],
            [1, "D1001", "张"],
            [2, "D1002", "李"],
        ],
    }],
    explanation="面经索引：`LIKE 'abc%'` 可走索引范围扫描；`LIKE '%abc'` 一般全表扫描。",
)

write_problem(
    "iv-019-remaining-slots",
    title="排班剩余号源数",
    difficulty="medium",
    tags=["面试", "LEFT JOIN", "GROUP BY", "容量"],
    task="""## 表结构

**schedules**：每个 `(schedule_id, slot_index)` 一行号源。  
**registrations**：已占用号源。

## 目标

统计每个 `schedule_id` 的总号源数、已占用数、剩余数。

要求：
- 返回 `schedule_id`, `total_cnt`, `used_cnt`, `left_cnt`
- 按 `schedule_id` 升序

## 提示

- 对 schedules 分组得 total；LEFT JOIN registrations 后 `COUNT(r.id)` 为 used
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS schedules;
CREATE TABLE schedules (
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL
);
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL
);
INSERT INTO schedules (schedule_id, slot_index) VALUES
(10, 1), (10, 2), (10, 3), (10, 4),
(11, 1), (11, 2);
INSERT INTO registrations (id, schedule_id, slot_index) VALUES
(1, 10, 1), (2, 10, 2), (3, 11, 1);
""",
    solution="""
SELECT s.schedule_id,
       COUNT(*) AS total_cnt,
       COUNT(r.id) AS used_cnt,
       COUNT(*) - COUNT(r.id) AS left_cnt
FROM schedules s
LEFT JOIN registrations r
  ON s.schedule_id = r.schedule_id AND s.slot_index = r.slot_index
GROUP BY s.schedule_id
ORDER BY s.schedule_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["schedule_id", "total_cnt", "used_cnt", "left_cnt"],
        "expected_rows": [
            [10, 4, 2, 2],
            [11, 2, 1, 1],
        ],
    }],
    explanation="面经挂号容量：总号源 − 已占用 = 剩余，支撑限流与放号决策。",
)

write_problem(
    "iv-020-multi-dept-same-day",
    title="同日挂多科室的患者",
    difficulty="medium",
    tags=["面试", "GROUP BY", "HAVING", "COUNT DISTINCT"],
    task="""## 表结构

**registrations**：`patient_id`, `dept_id`, `reg_date`（`YYYY-MM-DD`）

## 目标

找出在 **同一天** 挂了 **不少于 2 个不同科室** 的患者日期组合。

要求：
- 返回 `patient_id`, `reg_date`, `dept_cnt`
- 按 `patient_id`, `reg_date` 升序

## 提示

- `GROUP BY patient_id, reg_date HAVING COUNT(DISTINCT dept_id) >= 2`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  patient_id INTEGER NOT NULL,
  dept_id INTEGER NOT NULL,
  reg_date TEXT NOT NULL
);
INSERT INTO registrations (id, patient_id, dept_id, reg_date) VALUES
(1, 1, 10, '2026-07-01'),
(2, 1, 11, '2026-07-01'),
(3, 1, 10, '2026-07-01'),
(4, 1, 10, '2026-07-02'),
(5, 2, 10, '2026-07-01'),
(6, 2, 10, '2026-07-01'),
(7, 3, 10, '2026-07-01'),
(8, 3, 12, '2026-07-01'),
(9, 3, 13, '2026-07-01');
""",
    solution="""
SELECT patient_id, reg_date, COUNT(DISTINCT dept_id) AS dept_cnt
FROM registrations
GROUP BY patient_id, reg_date
HAVING COUNT(DISTINCT dept_id) >= 2
ORDER BY patient_id, reg_date;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["patient_id", "reg_date", "dept_cnt"],
        "expected_rows": [
            [1, "2026-07-01", 2],
            [3, "2026-07-01", 3],
        ],
    }],
    explanation="面经业务风控：同日跨科室异常挂号可用 DISTINCT 计数检出。",
)

write_problem(
    "iv-021-slot-gaps",
    title="号源序号缺口",
    difficulty="hard",
    tags=["面试", "自连接", "缺口", "序号"],
    task="""## 表结构

**schedules**：同一 `schedule_id` 下 `slot_index` 应为从 1 起的连续整数，但可能缺号。

## 目标

找出每个排班中「缺失的号源序号」（存在 `k` 与 `k+2`，但不存在 `k+1` 时，报告缺失的 `k+1`；更一般：存在 `slot_index = x`，不存在 `x+1`，且存在更大的序号）。

简化要求：返回所有满足「`slot_index = g` 缺失，但存在更小与更大号」的 `(schedule_id, missing_slot)`，其中 `missing_slot` 为某已存在号 `s` 的 `s+1`，且 `s+1` 不在表中，且存在 `> s+1` 的号。

要求：
- 返回 `schedule_id`, `missing_slot`
- 按两者升序

## 提示

- 从已有 `s` 出发检查 `s+1` 是否缺失且后面还有更大号
""",
    schema="""
DROP TABLE IF EXISTS schedules;
CREATE TABLE schedules (
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL
);
INSERT INTO schedules (schedule_id, slot_index) VALUES
(10, 1), (10, 2), (10, 4), (10, 5),
(11, 1), (11, 2), (11, 3),
(12, 1), (12, 3), (12, 4);
""",
    solution="""
SELECT s.schedule_id, s.slot_index + 1 AS missing_slot
FROM schedules s
WHERE NOT EXISTS (
  SELECT 1 FROM schedules x
  WHERE x.schedule_id = s.schedule_id AND x.slot_index = s.slot_index + 1
)
AND EXISTS (
  SELECT 1 FROM schedules y
  WHERE y.schedule_id = s.schedule_id AND y.slot_index > s.slot_index + 1
)
ORDER BY s.schedule_id, missing_slot;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["schedule_id", "missing_slot"],
        "expected_rows": [
            [10, 3],
            [12, 2],
        ],
    }],
    explanation="面经数据质量：连续号源放号后用缺口检测发现漏号/脏数据。",
)

write_problem(
    "iv-022-cancel-rate",
    title="科室取消率",
    difficulty="medium",
    tags=["面试", "CASE", "比率", "GROUP BY"],
    task="""## 表结构

**registrations**：`dept_id`, `status`（`ok` / `cancel`）

## 目标

计算各科室取消率（取消数 / 总挂号数），结果为整数百分比（向下取整）。

要求：
- 返回 `dept_id`, `total_cnt`, `cancel_cnt`, `cancel_pct`
- `cancel_pct = cancel_cnt * 100 / total_cnt`（整数除法）
- 按 `dept_id` 升序

## 提示

- SQLite 整数除法；或用 `CAST` 按题目要求取整
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  dept_id INTEGER NOT NULL,
  status TEXT NOT NULL
);
INSERT INTO registrations (id, dept_id, status) VALUES
(1, 1, 'ok'), (2, 1, 'ok'), (3, 1, 'cancel'), (4, 1, 'cancel'),
(5, 2, 'ok'), (6, 2, 'ok'), (7, 2, 'ok'), (8, 2, 'cancel'),
(9, 3, 'cancel'), (10, 3, 'cancel');
""",
    solution="""
SELECT dept_id,
       COUNT(*) AS total_cnt,
       SUM(CASE WHEN status = 'cancel' THEN 1 ELSE 0 END) AS cancel_cnt,
       SUM(CASE WHEN status = 'cancel' THEN 1 ELSE 0 END) * 100 / COUNT(*) AS cancel_pct
FROM registrations
GROUP BY dept_id
ORDER BY dept_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["dept_id", "total_cnt", "cancel_cnt", "cancel_pct"],
        "expected_rows": [
            [1, 4, 2, 50],
            [2, 4, 1, 25],
            [3, 2, 2, 100],
        ],
    }],
    explanation="面经运营指标：取消率等比率用条件聚合一次算出，避免多次扫表。",
)

write_problem(
    "iv-023-three-table-detail",
    title="三表连接挂号明细",
    difficulty="medium",
    tags=["面试", "多表JOIN", "明细"],
    task="""## 表结构

**patients** / **doctors** / **registrations**（含 `patient_id`, `doctor_id`, `created_at`）

## 目标

输出挂号明细：患者名、医生名、时间。

要求：
- 返回 `patient_name`, `doctor_name`, `created_at`
- 按 `created_at`, `patient_name` 升序

## 提示

- 两路 INNER JOIN
""",
    schema="""
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;
CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE doctors (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  patient_id INTEGER NOT NULL,
  doctor_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO patients (id, name) VALUES (1, '甲'), (2, '乙');
INSERT INTO doctors (id, name) VALUES (1, '张医生'), (2, '李医生');
INSERT INTO registrations (id, patient_id, doctor_id, created_at) VALUES
(1, 1, 1, '2026-07-01 09:00:00'),
(2, 2, 1, '2026-07-01 09:30:00'),
(3, 1, 2, '2026-07-01 10:00:00');
""",
    solution="""
SELECT p.name AS patient_name, d.name AS doctor_name, r.created_at
FROM registrations r
JOIN patients p ON r.patient_id = p.id
JOIN doctors d ON r.doctor_id = d.id
ORDER BY r.created_at, patient_name;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["patient_name", "doctor_name", "created_at"],
        "expected_rows": [
            ["甲", "张医生", "2026-07-01 09:00:00"],
            ["乙", "张医生", "2026-07-01 09:30:00"],
            ["甲", "李医生", "2026-07-01 10:00:00"],
        ],
    }],
    explanation="面经多表查询基本功：事实表关联维表输出可读明细，注意列别名避免重名。",
)

write_problem(
    "iv-024-hot-depts",
    title="热门科室过滤",
    difficulty="easy",
    tags=["面试", "HAVING", "GROUP BY"],
    task="""## 表结构

**registrations**：`dept_id`

## 目标

挂号量 **≥ 3** 的热门科室。

要求：
- 返回 `dept_id`, `cnt`
- 按 `cnt` 降序，`dept_id` 升序

## 提示

- `HAVING COUNT(*) >= 3`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  dept_id INTEGER NOT NULL
);
INSERT INTO registrations (id, dept_id) VALUES
(1, 1), (2, 1), (3, 1), (4, 1),
(5, 2), (6, 2),
(7, 3), (8, 3), (9, 3),
(10, 4);
""",
    solution="""
SELECT dept_id, COUNT(*) AS cnt
FROM registrations
GROUP BY dept_id
HAVING COUNT(*) >= 3
ORDER BY cnt DESC, dept_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["dept_id", "cnt"],
        "expected_rows": [[1, 4], [3, 3]],
    }],
    explanation="面经聚合过滤：WHERE 滤行前，HAVING 滤分组后；热门科室常用 HAVING。",
)

write_problem(
    "iv-025-distinct-patients",
    title="去重就诊人次",
    difficulty="easy",
    tags=["面试", "COUNT DISTINCT", "去重"],
    task="""## 表结构

**registrations**：`dept_id`, `patient_id`（同一患者可多次挂号）

## 目标

统计各科室 **去重患者数**（不是挂号次数）。

要求：
- 返回 `dept_id`, `patient_cnt`
- 按 `dept_id` 升序

## 提示

- `COUNT(DISTINCT patient_id)`
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  dept_id INTEGER NOT NULL,
  patient_id INTEGER NOT NULL
);
INSERT INTO registrations (id, dept_id, patient_id) VALUES
(1, 1, 10), (2, 1, 10), (3, 1, 11),
(4, 2, 10), (5, 2, 12), (6, 2, 12), (7, 2, 13);
""",
    solution="""
SELECT dept_id, COUNT(DISTINCT patient_id) AS patient_cnt
FROM registrations
GROUP BY dept_id
ORDER BY dept_id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["dept_id", "patient_cnt"],
        "expected_rows": [[1, 2], [2, 3]],
    }],
    explanation="面经指标口径：挂号量 vs 去重人数不同，面试常追问用 COUNT DISTINCT。",
)

write_problem(
    "iv-026-adjacent-slots",
    title="相邻号源成对列出",
    difficulty="medium",
    tags=["面试", "自连接", "号源"],
    task="""## 表结构

**schedules**：`schedule_id`, `slot_index`

## 目标

列出同一排班下 **相邻** 号源对（`slot_b = slot_a + 1`）。

要求：
- 返回 `schedule_id`, `slot_a`, `slot_b`
- 按 `schedule_id`, `slot_a` 升序

## 提示

- 自连接：`a.slot_index + 1 = b.slot_index`
""",
    schema="""
DROP TABLE IF EXISTS schedules;
CREATE TABLE schedules (
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL
);
INSERT INTO schedules (schedule_id, slot_index) VALUES
(10, 1), (10, 2), (10, 3), (10, 5),
(11, 1), (11, 2);
""",
    solution="""
SELECT a.schedule_id, a.slot_index AS slot_a, b.slot_index AS slot_b
FROM schedules a
JOIN schedules b
  ON a.schedule_id = b.schedule_id
 AND a.slot_index + 1 = b.slot_index
ORDER BY a.schedule_id, slot_a;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["schedule_id", "slot_a", "slot_b"],
        "expected_rows": [
            [10, 1, 2],
            [10, 2, 3],
            [11, 1, 2],
        ],
    }],
    explanation="面经自连接：相邻号源可用于「连号锁号」或缺口检测的前一步。",
)

write_problem(
    "iv-027-coalesce-phone",
    title="手机号缺省展示",
    difficulty="easy",
    tags=["面试", "COALESCE", "NULL"],
    task="""## 表结构

**patients**：`id`, `name`, `phone`（可空）

## 目标

导出联系人列表：无手机号时显示 `'未填写'`。

要求：
- 返回 `id`, `name`, `phone_display`
- 按 `id` 升序

## 提示

- `COALESCE(phone, '未填写')`
""",
    schema="""
DROP TABLE IF EXISTS patients;
CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT
);
INSERT INTO patients (id, name, phone) VALUES
(1, '甲', '13800000001'),
(2, '乙', NULL),
(3, '丙', '13800000003');
""",
    solution="""
SELECT id, name, COALESCE(phone, '未填写') AS phone_display
FROM patients
ORDER BY id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "name", "phone_display"],
        "expected_rows": [
            [1, "甲", "13800000001"],
            [2, "乙", "未填写"],
            [3, "丙", "13800000003"],
        ],
    }],
    explanation="面经 NULL 处理：展示层用 COALESCE/IFNULL 给缺省值，避免把 NULL 当成业务值。",
)

write_problem(
    "iv-028-lock-candidates",
    title="待加锁的号源行",
    difficulty="medium",
    tags=["面试", "当前读", "FOR UPDATE", "状态"],
    task="""## 表结构

**slots**：`schedule_id`, `slot_index`, `status`（`open` / `held` / `sold`）

业务要在事务里对「仍 open 的指定排班号源」做 `SELECT ... FOR UPDATE`。本题先写出 **将被锁住的候选行** 查询。

## 目标

查出 `schedule_id = 10` 且 `status = 'open'` 的号源。

要求：
- 返回 `schedule_id`, `slot_index`, `status`
- 按 `slot_index` 升序

## 提示

- 当前读前的定位查询；OJ 只验证 SELECT 结果集
""",
    schema="""
DROP TABLE IF EXISTS slots;
CREATE TABLE slots (
  schedule_id INTEGER NOT NULL,
  slot_index INTEGER NOT NULL,
  status TEXT NOT NULL
);
INSERT INTO slots (schedule_id, slot_index, status) VALUES
(10, 1, 'sold'),
(10, 2, 'open'),
(10, 3, 'held'),
(10, 4, 'open'),
(11, 1, 'open');
""",
    solution="""
SELECT schedule_id, slot_index, status
FROM slots
WHERE schedule_id = 10 AND status = 'open'
ORDER BY slot_index;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["schedule_id", "slot_index", "status"],
        "expected_rows": [
            [10, 2, "open"],
            [10, 4, "open"],
        ],
    }],
    explanation="面经 FOR UPDATE：先等值定位待锁行（排班+状态），再当前读；唯一索引/主键定位锁粒度更可控。",
)

write_problem(
    "iv-029-between-hours",
    title="营业时段内的挂号",
    difficulty="easy",
    tags=["面试", "BETWEEN", "时间"],
    task="""## 表结构

**registrations**：`id`, `created_at`（同一天内时间）

## 目标

筛选当天 **09:00:00 至 11:30:00（含两端）** 的挂号。

要求：
- 返回 `id`, `created_at`
- 按 `id` 升序
- 可用 `BETWEEN` 或等价比较

## 提示

- 时间存 TEXT 时可直接字符串比较
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL
);
INSERT INTO registrations (id, created_at) VALUES
(1, '2026-07-01 08:59:59'),
(2, '2026-07-01 09:00:00'),
(3, '2026-07-01 10:15:00'),
(4, '2026-07-01 11:30:00'),
(5, '2026-07-01 11:30:01');
""",
    solution="""
SELECT id, created_at
FROM registrations
WHERE created_at BETWEEN '2026-07-01 09:00:00' AND '2026-07-01 11:30:00'
ORDER BY id;
""",
    cases=[{
        "id": "1",
        "expected_columns": ["id", "created_at"],
        "expected_rows": [
            [2, "2026-07-01 09:00:00"],
            [3, "2026-07-01 10:15:00"],
            [4, "2026-07-01 11:30:00"],
        ],
    }],
    explanation="面经范围条件：营业时段过滤用 BETWEEN/闭区间，注意端点是否包含。",
)

write_problem(
    "iv-030-revisit-gap",
    title="二次挂号最短间隔",
    difficulty="hard",
    tags=["面试", "自连接", "时间差", "风控"],
    task="""## 表结构

**registrations**：同一 `patient_id` 可有多次挂号，`created_at` 为时间。

## 目标

找出「同一患者两次挂号间隔 **严格小于 30 分钟**」的记录对。

要求：
- 返回 `patient_id`, `id_first`, `id_second`, `created_first`, `created_second`
- `id_first` 对应较早那次（`created_at` 更小；同时刻则 `id` 更小）
- 只输出 `id_first < id_second` 且时间差 < 30 分钟的对
- 按 `patient_id`, `id_first`, `id_second` 升序

时间差可用：后时间 ≥ 前时间，且后时间 < 前时间加 30 分钟。  
（文本时间可借助成对比较：存在即可按给定样例验证。）

## 提示

- 自连接同患者；样例中 30 分钟边界用字面时间判断
""",
    schema="""
DROP TABLE IF EXISTS registrations;
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY,
  patient_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
INSERT INTO registrations (id, patient_id, created_at) VALUES
(1, 1, '2026-07-01 09:00:00'),
(2, 1, '2026-07-01 09:20:00'),
(3, 1, '2026-07-01 09:50:00'),
(4, 2, '2026-07-01 09:00:00'),
(5, 2, '2026-07-01 09:30:00'),
(6, 2, '2026-07-01 09:29:00');
""",
    solution="""
SELECT a.patient_id,
       a.id AS id_first,
       b.id AS id_second,
       a.created_at AS created_first,
       b.created_at AS created_second
FROM registrations a
JOIN registrations b
  ON a.patient_id = b.patient_id
 AND a.id < b.id
 AND a.created_at <= b.created_at
 AND b.created_at < datetime(a.created_at, '+30 minutes')
ORDER BY a.patient_id, id_first, id_second;
""",
    cases=[{
        "id": "1",
        "expected_columns": [
            "patient_id", "id_first", "id_second", "created_first", "created_second"
        ],
        "expected_rows": [
            [1, 1, 2, "2026-07-01 09:00:00", "2026-07-01 09:20:00"],
            [2, 4, 6, "2026-07-01 09:00:00", "2026-07-01 09:29:00"],
        ],
    }],
    explanation="面经风控：短时间重复挂号可疑；自连接 + 时间窗口，注意 30 分钟边界（本题严格小于）。",
)


def update_manifest() -> None:
    manifest_path = BANK / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["name"] = "SQL OJ Main"
    data["version"] = "1.2.0"
    data["source"] = "pta+leetcode+interview"
    iv = sorted(
        p.name for p in PROBLEMS.iterdir() if p.is_dir() and p.name.startswith("iv-")
    )
    existing = [x for x in data.get("problems", []) if not str(x).startswith("iv-")]
    data["problems"] = existing + iv
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifest problems={len(data['problems'])} (iv={len(iv)})")


if __name__ == "__main__":
    update_manifest()
