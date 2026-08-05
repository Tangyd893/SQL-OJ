#!/usr/bin/env python3
"""补导入剩余 6 题 + 刷新已有 lc 题的 schema.sql / solution.sql。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_external_problems import (
    fetch_leetcode_detail,
    build_leetcode_problem,
    load_handwritten,
    pick_sqlite_solution,
    prepare_leetcode_schema_statements,
    load_existing_index,
    write_problem,
    update_manifest,
    is_duplicate,
)
from leetcode_schema import prepare_leetcode_schema_statements as prep  # noqa: F401

BANK = ROOT / "banks" / "main"
SLUGS = [
    "dynamic-unpivoting-of-a-table",
    "count-artist-occurrences-on-spotify-ranking-list",
    "top-three-wineries",
    "find-trending-hashtags",
    "find-trending-hashtags-ii",
    "invalid-tweets-ii",
]


def refresh_lc_schemas() -> int:
    n = 0
    for prob_dir in (BANK / "problems").iterdir():
        if not prob_dir.is_dir() or not prob_dir.name.startswith("lc-"):
            continue
        meta = json.loads((prob_dir / "meta.json").read_text(encoding="utf-8"))
        slug = meta.get("externalSlug")
        if not slug:
            continue
        detail = fetch_leetcode_detail(slug)
        if not detail:
            continue
        schemas = detail.get("mysqlSchemas") or []
        fixed = "\n\n".join(prepare_leetcode_schema_statements(schemas)) + "\n"
        (prob_dir / "schema.sql").write_text(fixed, encoding="utf-8")
        n += 1
    return n


def main() -> int:
    load_handwritten()
    manifest_ids, existing = load_existing_index(BANK)
    added = []

    for slug in SLUGS:
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
        if is_duplicate(built, existing):
            # 已存在则只刷新文件
            pid = next(
                (m["id"] for m in existing.values() if m.get("externalSlug") == slug),
                built["id"],
            )
            built["id"] = pid
            built["meta"]["id"] = pid
        write_problem(BANK, built)
        if built["id"] not in manifest_ids:
            manifest_ids.append(built["id"])
        existing[built["id"]] = built["meta"]
        added.append(built["id"])
        print(f"ok {slug} -> {built['id']}")

    update_manifest(BANK, manifest_ids)
    print(f"\nAdded/updated {len(added)} slugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
