#!/usr/bin/env python3
"""Re-import LC problems whose stored solution/reference is stale."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_external_problems import (
    build_leetcode_problem,
    fetch_leetcode_detail,
    load_handwritten,
    pick_sqlite_solution,
    write_problem,
)

BANK = ROOT / "banks" / "pta-150"
REPORT = BANK / "alignment-report.json"

FAIL_SLUGS = [
    "average-salary-departments-vs-company",
    "tournament-winners",
    "the-latest-login-in-2020",
    "products-with-three-or-more-orders-in-two-consecutive-years",
    "find-cities-in-each-state",
    "year-on-year-growth-rate",
    "first-letter-capitalization-ii",
    "report-contiguous-dates",
    "movie-rating",
    "hopper-company-queries-i",
    "league-statistics",
    "the-number-of-seniors-and-juniors-to-join-the-company-ii",
    "employee-task-duration-and-concurrent-tasks",
    "bitwise-user-permissions-analysis",
    "longest-team-pass-streak",
    "find-circular-gift-exchange-chains",
    "find-products-with-three-consecutive-digits",
]


def main() -> int:
    load_handwritten()
    for slug in FAIL_SLUGS:
        detail = fetch_leetcode_detail(slug)
        if not detail:
            print(f"skip {slug}: no detail")
            continue
        sql = pick_sqlite_solution(slug, detail.get("mysqlSchemas") or [])
        if not sql:
            print(f"skip {slug}: no solution")
            continue
        built = build_leetcode_problem(detail, slug, sql)
        if not built:
            print(f"skip {slug}: build failed")
            continue
        # keep existing id
        for prob_dir in (BANK / "problems").iterdir():
            meta_path = prob_dir / "meta.json"
            if not meta_path.is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("externalSlug") == slug:
                built["id"] = meta["id"]
                built["meta"]["id"] = meta["id"]
                break
        write_problem(BANK, built)
        print(f"refreshed {slug} -> {built['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
