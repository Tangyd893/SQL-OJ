#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
校验外部题库：为每个测试点推导 reference_sql，在 SQLite 沙箱中验证能否得到期望结果。

用法:
  python scripts/verify_bank.py
  python scripts/verify_bank.py --bank banks/pta-150 --write-back
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ddl_verify import build_verify_sql
from leetcode_schema import exec_schema
from import_external_problems import _adapt_reference_sql
from mysql_compat import mysql_to_sqlite, strip_sql_comments
from reference_sql import derive_reference_sql
from sql_split import split_sql


@dataclass
class CaseReport:
    problem_id: str
    case_id: str
    ok: bool
    message: str
    reference_sql: str | None = None


def normalize_rows(rows: list[list]) -> list[list]:
    out = []
    for row in rows:
        nr = []
        for v in row:
            if isinstance(v, float):
                nr.append(round(v, 6))
            else:
                nr.append(v)
        out.append(nr)
    return out


def adapt_sql_for_problem(problem_id: str, sql: str) -> str:
    if problem_id.startswith("lc-"):
        return _adapt_reference_sql(sql)
    return mysql_to_sqlite(sql)


def run_reference(conn: sqlite3.Connection, sql: str, problem_id: str = "") -> tuple[list[str], list[list]]:
    sql = adapt_sql_for_problem(problem_id, sql)
    statements = split_sql(sql)
    if not statements:
        raise ValueError("empty sql")
    last_select = None
    for stmt in statements:
        if re.match(r"^(SELECT|WITH|EXPLAIN|PRAGMA)", stmt, re.I):
            last_select = stmt
        else:
            conn.execute(stmt)
    if not last_select:
        raise ValueError("no select in reference sql")
    cur = conn.cursor()
    cur.execute(last_select)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = [list(r) for r in cur.fetchall()]
    return cols, rows


def verify_case(
    problem_id: str,
    problem_schema: str,
    case: dict,
    reference_sql: str,
) -> CaseReport:
    case_id = str(case.get("id", "?"))
    schema = case.get("schema") or problem_schema
    exp_cols = case.get("expected_columns") or []
    exp_rows = case.get("expected_rows") or []

    conn = sqlite3.connect(":memory:")
    try:
        schema = case.get("schema") or problem_schema
        exec_schema(conn, schema)
        if case.get("seed"):
            for stmt in split_sql(mysql_to_sqlite(case["seed"])):
                if stmt.strip():
                    conn.execute(stmt)
        cols, rows = run_reference(conn, reference_sql, problem_id)
    except Exception as e:
        conn.close()
        return CaseReport(problem_id, case_id, False, f"执行失败: {e}", reference_sql)
    conn.close()

    # 空结果测试点：只校验行数为 0
    if not exp_rows:
        if len(rows) == 0:
            return CaseReport(problem_id, case_id, True, "ok (empty)", reference_sql)
        return CaseReport(
            problem_id,
            case_id,
            False,
            f"期望空结果 实际 {len(rows)} 行",
            reference_sql,
        )

    if [c.lower() for c in cols] != [c.lower() for c in exp_cols]:
        return CaseReport(
            problem_id,
            case_id,
            False,
            f"列不匹配 期望{exp_cols} 实际{cols}",
            reference_sql,
        )

    if normalize_rows(rows) != normalize_rows(exp_rows):
        return CaseReport(
            problem_id,
            case_id,
            False,
            f"行不匹配 期望{len(exp_rows)}行 实际{len(rows)}行",
            reference_sql,
        )

    return CaseReport(problem_id, case_id, True, "ok", reference_sql)


def fix_expected_from_reference(
    problem_schema: str,
    case: dict,
    reference_sql: str,
) -> tuple[list[str], list[list]] | None:
    """用 reference_sql 执行结果覆盖期望输出。"""
    schema = case.get("schema") or problem_schema
    conn = sqlite3.connect(":memory:")
    try:
        schema = case.get("schema") or problem_schema
        exec_schema(conn, schema)
        if case.get("seed"):
            for stmt in split_sql(mysql_to_sqlite(case["seed"])):
                if stmt.strip():
                    conn.execute(stmt)
        cols, rows = run_reference(conn, reference_sql, problem_id)
    except Exception:
        conn.close()
        return None
    conn.close()
    return cols, rows


def load_solutions_from_mysql() -> dict[str, str]:
    try:
        import pymysql
    except ImportError:
        return {}

    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="oj_user",
            password="ojpass",
            database="sql_oj",
            charset="utf8mb4",
        )
        cur = conn.cursor()
        cur.execute("SELECT slug, solution, test_cases FROM problems")
        out: dict[str, str] = {}
        desc_map: dict[str, dict[str, str]] = {}
        for slug, sol, tc in cur.fetchall():
            if sol:
                out[slug] = sol
            desc_map[slug] = {
                str(c["id"]): c.get("description", "")
                for c in json.loads(tc)
            }
        conn.close()
        return out, desc_map  # type: ignore
    except Exception:
        return {}, {}


def verify_bank(bank: Path, write_back: bool, fix_expected: bool) -> dict:
    solutions, desc_from_mysql = load_solutions_from_mysql()

    reports: list[CaseReport] = []
    total_cases = 0
    problems_dir = bank / "problems"

    for prob_dir in sorted(problems_dir.iterdir()):
        if not prob_dir.is_dir():
            continue
        slug = prob_dir.name
        schema_path = prob_dir / "schema.sql"
        cases_path = prob_dir / "cases.json"
        if not schema_path.exists() or not cases_path.exists():
            continue

        schema = schema_path.read_text(encoding="utf-8")
        cases_doc = json.loads(cases_path.read_text(encoding="utf-8"))
        cases = cases_doc.get("cases", [])
        solution = solutions.get(slug, "")
        mysql_desc = desc_from_mysql.get(slug, {})
        changed = False

        for case in cases:
            total_cases += 1
            case_id = str(case.get("id", "?"))
            if not case.get("reference_sql"):
                desc = case.get("description") or mysql_desc.get(case_id, "")
                ref = derive_reference_sql(
                    solution,
                    {"id": case_id, "description": desc},
                )
                if ref:
                    case["reference_sql"] = ref
                    changed = True
            else:
                ref = case["reference_sql"]

            ref = case.get("reference_sql") or solution
            verify_extra = build_verify_sql(slug, case, ref or "")
            if verify_extra:
                ref = f"{ref.rstrip(';')}; {verify_extra}"
            elif ref and not re.search(
                r"\b(SELECT|WITH)\b", strip_sql_comments(ref), re.I
            ):
                cols = case.get("expected_columns") or []
                if cols and case.get("expected_rows") is not None:
                    if not re.search(r"\bCREATE\b", strip_sql_comments(ref), re.I):
                        schema_text = case.get("schema") or schema
                        m = re.search(r"CREATE\s+TABLE\s+(\w+)", schema_text, re.I)
                        if m:
                            table = m.group(1)
                            col_list = ", ".join(cols)
                            ref = f"{ref.rstrip(';')}; SELECT {col_list} FROM {table}"

            if fix_expected and ref:
                fixed = fix_expected_from_reference(schema, case, ref)
                if fixed:
                    cols, rows = fixed
                    case["expected_columns"] = cols
                    case["expected_rows"] = rows
                    changed = True

            report = verify_case(slug, schema, case, ref or solution)
            reports.append(report)

        if write_back and changed:
            cases_path.write_text(
                json.dumps(cases_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    passed = sum(1 for r in reports if r.ok)
    failed = [asdict(r) for r in reports if not r.ok]

    summary = {
        "bank": str(bank),
        "problems": len(list(problems_dir.iterdir())),
        "cases": total_cases,
        "passed": passed,
        "failed_count": len(failed),
        "failed": failed[:100],
    }

    report_path = bank / "verify-report.json"
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", default=str(ROOT / "banks" / "pta-150"))
    parser.add_argument(
        "--write-back",
        action="store_true",
        help="将推导出的 reference_sql 写回 cases.json",
    )
    parser.add_argument(
        "--fix-expected",
        action="store_true",
        help="用 reference_sql 执行结果修正 expected_columns/rows",
    )
    args = parser.parse_args()

    bank = Path(args.bank)
    if not bank.is_dir():
        print(f"题库不存在: {bank}")
        sys.exit(1)

    summary = verify_bank(bank, args.write_back, args.fix_expected)
    print(
        f"校验完成: {summary['passed']}/{summary['cases']} 通过, "
        f"失败 {summary['failed_count']}"
    )
    print(f"报告: {bank / 'verify-report.json'}")
    if summary["failed_count"]:
        for item in summary["failed"][:15]:
            print(f"  FAIL {item['problem_id']} #{item['case_id']}: {item['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
