#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从旧 MySQL 主库导出 150 题，转换为外部 SQLite 题库格式。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("pip install pymysql")
    sys.exit(1)

from enrich_test_cases import enrich_test_cases
from reference_sql import derive_reference_sql

ROOT = Path(__file__).resolve().parent.parent
OUT_BANK = ROOT / "banks" / "main"

DB = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "oj_user"),
    "password": os.environ.get("DB_PASSWORD", "ojpass"),
    "database": os.environ.get("DB_NAME", "sql_oj"),
    "charset": "utf8mb4",
}


from mysql_compat import mysql_to_sqlite


def expected_to_case(tc: dict, solution: str = "") -> dict | None:
    if tc.get("judge") is False:
        return None
    expected = tc.get("expected")
    if expected is None:
        return None

    case: dict = {"id": str(tc.get("id", "1")), "seed": ""}

    desc = tc.get("description", "")
    if desc:
        case["description"] = desc
    if solution:
        ref = derive_reference_sql(solution, tc)
        if ref:
            case["reference_sql"] = ref

    per_schema = tc.get("schema_sql") or tc.get("setup_sql")
    if per_schema:
        case["schema"] = mysql_to_sqlite(per_schema)

    if not expected:
        case["expected_columns"] = []
        case["expected_rows"] = []
        return case

    columns = list(expected[0].keys())
    rows = [[row.get(col) for col in columns] for row in expected]
    case["expected_columns"] = columns
    case["expected_rows"] = rows
    return case


def build_task_md(problem: dict) -> str:
    parts = [problem.get("description", "").strip()]
    hints = problem.get("hints")
    if hints:
        if isinstance(hints, list):
            parts.append("\n\n## 提示\n\n" + "\n".join(f"- {h}" for h in hints))
        else:
            parts.append("\n\n## 提示\n\n" + str(hints))
    expl = problem.get("explanation")
    if expl:
        parts.append("\n\n## 解析\n\n" + str(expl).strip())
    return "\n".join(p for p in parts if p).strip() + "\n"


def convert_problem(problem: dict) -> None:
    enrich_test_cases(problem)
    slug = problem["slug"]
    dest = OUT_BANK / "problems" / slug
    dest.mkdir(parents=True, exist_ok=True)

    tags = problem.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = [tags]

    meta = {
        "id": slug,
        "title": problem["title"],
        "difficulty": problem["difficulty"],
        "tags": tags,
    }
    (dest / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (dest / "task.md").write_text(build_task_md(problem), encoding="utf-8")
    (dest / "schema.sql").write_text(
        mysql_to_sqlite(problem.get("schema_sql", "")) + "\n", encoding="utf-8"
    )

    cases = []
    solution = problem.get("solution") or ""
    for tc in problem.get("test_cases", []):
        converted = expected_to_case(tc, solution)
        if converted:
            cases.append(converted)

    if not cases:
        cases = [{"id": "1", "seed": "", "expected_columns": [], "expected_rows": []}]

    (dest / "cases.json").write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_problems() -> list[dict]:
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                """
                SELECT p.slug, p.title, p.difficulty, p.tags, p.description,
                       p.schema_sql, p.solution, p.test_cases, p.hints,
                       p.explanation, p.sort_order, c.slug AS category
                FROM problems p
                JOIN categories c ON c.id = p.category_id
                ORDER BY p.sort_order, p.id
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    problems = []
    for row in rows:
        tags = row.get("tags")
        if isinstance(tags, str):
            tags = json.loads(tags)
        test_cases = row.get("test_cases")
        if isinstance(test_cases, str):
            test_cases = json.loads(test_cases)
        hints = row.get("hints")
        if isinstance(hints, str) and hints.startswith("["):
            hints = json.loads(hints)
        problems.append(
            {
                **row,
                "tags": tags or [],
                "test_cases": test_cases or [],
                "hints": hints,
            }
        )
    return problems


def main() -> None:
    problems = fetch_problems()
    print(f"Fetched {len(problems)} problems from MySQL")

    if OUT_BANK.exists():
        import shutil

        shutil.rmtree(OUT_BANK)
    (OUT_BANK / "problems").mkdir(parents=True)

    slugs = []
    for p in problems:
        convert_problem(p)
        slugs.append(p["slug"])
        print(f"  {p['slug']}")

    manifest = {
        "name": "PTA SQL 150",
        "version": "1.0.0",
        "source": "mysql-export",
        "problems": slugs,
    }
    (OUT_BANK / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote bank to {OUT_BANK}")


if __name__ == "__main__":
    main()
