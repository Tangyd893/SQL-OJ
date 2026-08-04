#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量检查：题目描述 (task.md) · 题解 (solution.sql) · 测试点 (cases.json) 对齐。

检查项:
  1. task.md 使用「## 目标」而非「## 任务」
  2. solution.sql 与测试点 1 的 reference_sql 一致
  3. 各测试点 reference_sql 可执行且结果与 expected 一致
  4. 题解 SQL 经测试点适配后能通过全部测试点（模拟判题）
  5. task.md 目标与测试点 1 reference_sql 过滤条件一致（dept 等）

用法:
  python scripts/check_alignment.py
  python scripts/check_alignment.py --bank banks/pta-150 --fix
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_consistency import norm_sql
from leetcode_schema import exec_schema
from export_mysql_bank import mysql_to_sqlite
from sql_adapt import adapt_user_sql_for_case
from verify_bank import CaseReport, adapt_sql_for_problem, normalize_rows, run_reference, verify_case
from sql_split import split_sql


@dataclass
class Issue:
    level: str  # error | warn
    category: str
    problem_id: str
    message: str


@dataclass
class AlignmentReport:
    bank: str
    problems: int = 0
    cases: int = 0
    solution_pass_all: int = 0
    reference_ok: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)


DEPT_IN_TASK = re.compile(r"查询\s*\*{0,2}([^*\n]+?)\*{0,2}")
DEPT_IN_REF = re.compile(r"(?i)\bdept\s*=\s*['\"]([^'\"]+)['\"]")


def load_problem(prob_dir: Path) -> dict | None:
    cases_path = prob_dir / "cases.json"
    if not cases_path.exists():
        return None
    return {
        "id": prob_dir.name,
        "dir": prob_dir,
        "cases": json.loads(cases_path.read_text(encoding="utf-8")).get("cases", []),
        "task": (prob_dir / "task.md").read_text(encoding="utf-8"),
        "schema": (prob_dir / "schema.sql").read_text(encoding="utf-8"),
        "solution": (prob_dir / "solution.sql").read_text(encoding="utf-8")
        if (prob_dir / "solution.sql").exists()
        else "",
    }


def baseline_ref(cases: list[dict]) -> str | None:
    for c in cases:
        if str(c.get("id")) == "1":
            ref = (c.get("reference_sql") or "").strip()
            if ref:
                return ref
    for c in cases:
        ref = (c.get("reference_sql") or "").strip()
        if ref:
            return ref
    return None


def extract_task_target(task: str) -> str | None:
    if "## 提示" in task:
        m = DEPT_IN_REF.search(task.split("## 提示", 1)[1])
        if m:
            return m.group(1)

    if "## 目标" in task:
        section = task.split("## 目标", 1)[1].split("##")[0]
    elif "## 任务" in task:
        section = task.split("## 任务", 1)[1].split("##")[0]
    elif "## 需求" in task:
        section = task.split("## 需求", 1)[1].split("##")[0]
    else:
        section = task

    for pat in (r"\*\*([^*]{1,20})\*\*", r"['\"]([^'\"]{1,20})['\"]"):
        m = re.search(pat, section)
        if m:
            val = m.group(1).strip()
            if val and not val.startswith("工资") and "条件" not in val:
                return val
    return None


def effective_sql(problem_id: str, problem_schema: str, case: dict, sql: str) -> str:
    from ddl_verify import build_verify_sql

    case_hint = {**case, "schema": case.get("schema") or problem_schema}
    extra = build_verify_sql(problem_id, case_hint, sql)
    if extra:
        return f"{sql.rstrip().rstrip(';')}; {extra}"
    return sql


def extract_ref_dept(ref: str) -> str | None:
    m = DEPT_IN_REF.search(ref or "")
    return m.group(1) if m else None


def verify_user_case(problem_id: str, problem_schema: str, case: dict, user_sql: str) -> CaseReport:
    case_id = str(case.get("id", "?"))
    schema = case.get("schema") or problem_schema
    exp_cols = case.get("expected_columns") or []
    exp_rows = case.get("expected_rows") or []

    conn = sqlite3.connect(":memory:")
    try:
        exec_schema(conn, schema)
        if case.get("seed"):
            for stmt in split_sql(mysql_to_sqlite(case["seed"])):
                if stmt.strip():
                    conn.execute(stmt)
        cols, rows = run_reference(conn, user_sql, problem_id)
    except Exception as e:
        conn.close()
        return CaseReport("", case_id, False, f"执行失败: {e}", user_sql)
    conn.close()

    if not exp_rows:
        if len(rows) == 0:
            return CaseReport("", case_id, True, "ok (empty)", user_sql)
        return CaseReport("", case_id, False, f"期望空结果 实际 {len(rows)} 行", user_sql)

    if [c.lower() for c in cols] != [c.lower() for c in exp_cols]:
        return CaseReport("", case_id, False, f"列不匹配 期望{exp_cols} 实际{cols}", user_sql)

    if normalize_rows(rows) != normalize_rows(exp_rows):
        return CaseReport(
            "",
            case_id,
            False,
            f"行不匹配 期望{len(exp_rows)}行 实际{len(rows)}行",
            user_sql,
        )

    return CaseReport("", case_id, True, "ok", user_sql)


def check_problem(prob: dict, report: AlignmentReport) -> None:
    pid = prob["id"]
    cases = prob["cases"]
    schema = prob["schema"]
    task = prob["task"]
    solution = prob["solution"].strip()
    base = baseline_ref(cases)

    if "## 任务" in task:
        report.issues.append(
            Issue("warn", "task", pid, "task.md 仍使用「## 任务」，应改为「## 目标」")
        )

    if not cases:
        report.issues.append(Issue("error", "cases", pid, "无测试点"))
        return

    if not base:
        report.issues.append(Issue("error", "cases", pid, "测试点 1 无 reference_sql"))
        return

    for case in cases:
        cid = str(case.get("id", "?"))
        ref = (case.get("reference_sql") or "").strip()
        if not ref:
            report.issues.append(
                Issue("error", "reference", pid, f"测试点 {cid} 缺少 reference_sql")
            )
            continue
        vr = verify_case(pid, schema, case, effective_sql(pid, schema, case, ref))
        if vr.ok:
            report.reference_ok += 1
        else:
            report.issues.append(
                Issue(
                    "error",
                    "reference",
                    pid,
                    f"测试点 {cid} reference 与 expected 不一致: {vr.message}",
                )
            )

    if not solution:
        report.issues.append(Issue("error", "solution", pid, "缺少 solution.sql"))
    elif norm_sql(solution) != norm_sql(base):
        report.issues.append(
            Issue("error", "solution", pid, "solution.sql 与测试点 1 reference_sql 不一致")
        )

    task_target = extract_task_target(task)
    ref_dept = extract_ref_dept(base)
    if task_target and ref_dept and task_target != ref_dept:
        report.issues.append(
            Issue(
                "error",
                "task",
                pid,
                f"题目目标「{task_target}」与测试点1 reference 部门「{ref_dept}」不一致",
            )
        )

    sql_to_judge = solution or base
    all_pass = True
    for case in cases:
        cid = str(case.get("id", "?"))
        adapted = adapt_user_sql_for_case(
            sql_to_judge, base, case.get("reference_sql")
        )
        ur = verify_user_case(pid, schema, case, effective_sql(pid, schema, case, adapted))
        if not ur.ok:
            all_pass = False
            report.issues.append(
                Issue(
                    "error",
                    "judge",
                    pid,
                    f"题解经适配后在测试点 {cid} 失败: {ur.message}",
                )
            )
    if all_pass:
        report.solution_pass_all += 1


def fix_problem(prob: dict) -> list[str]:
    actions: list[str] = []
    prob_dir: Path = prob["dir"]
    cases = prob["cases"]
    base = baseline_ref(cases)

    task_path = prob_dir / "task.md"
    task = prob["task"]
    if "## 任务" in task:
        task_path.write_text(
            task.replace("## 任务", "## 目标"), encoding="utf-8", newline="\n"
        )
        actions.append("task→目标")

    if base:
        solution_path = prob_dir / "solution.sql"
        content = base.rstrip() + "\n"
        existing = (
            solution_path.read_text(encoding="utf-8").strip()
            if solution_path.exists()
            else ""
        )
        if existing != content.strip():
            solution_path.write_text(content, encoding="utf-8", newline="\n")
            actions.append("solution.sql 同步")

    return actions


def run_alignment(bank: Path, do_fix: bool) -> AlignmentReport:
    report = AlignmentReport(bank=str(bank))
    problems_dir = bank / "problems"
    fixed: list[str] = []

    for prob_dir in sorted(problems_dir.iterdir()):
        if not prob_dir.is_dir():
            continue
        prob = load_problem(prob_dir)
        if not prob:
            continue

        if do_fix:
            acts = fix_problem(prob)
            if acts:
                fixed.append(f"{prob['id']}: {', '.join(acts)}")
                prob = load_problem(prob_dir) or prob

        report.problems += 1
        report.cases += len(prob["cases"])
        check_problem(prob, report)

    if do_fix and fixed:
        print(f"已自动修复 {len(fixed)} 题:")
        for line in fixed[:25]:
            print(f"  {line}")
        if len(fixed) > 25:
            print(f"  …另有 {len(fixed) - 25} 题")

    return report


def print_report(report: AlignmentReport) -> None:
    print("=" * 60)
    print("题目 · 题解 · 测试点 对齐检查")
    print("=" * 60)
    print(f"题库: {report.bank}")
    print(f"题目: {report.problems} · 测试点: {report.cases}")
    print(f"reference 验证通过: {report.reference_ok}/{report.cases}")
    print(f"题解全测试点通过: {report.solution_pass_all}/{report.problems}")

    errors = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warn"]
    print(f"\n问题: {len(errors)} 错误, {len(warns)} 警告")

    if errors:
        print("\n[错误]")
        for i in errors[:40]:
            print(f"  {i.problem_id} [{i.category}] {i.message}")
        if len(errors) > 40:
            print(f"  …另有 {len(errors) - 40} 条")
    if warns:
        print("\n[警告]")
        for i in warns[:15]:
            print(f"  {i.problem_id} [{i.category}] {i.message}")

    print(f"\n[{'PASS' if report.ok else 'FAIL'}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="题目/题解/测试点对齐检查")
    parser.add_argument("--bank", default=str(ROOT / "banks" / "pta-150"))
    parser.add_argument("--fix", action="store_true", help="修复 task 标题与 solution.sql")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    bank = Path(args.bank)
    report = run_alignment(bank, do_fix=args.fix)

    out = bank / "alignment-report.json"
    payload = {
        **{k: v for k, v in asdict(report).items() if k != "issues"},
        "ok": report.ok,
        "issues": [asdict(i) for i in report.issues],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(report)
        print(f"报告: {out}")

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
