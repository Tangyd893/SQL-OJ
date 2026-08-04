#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补全失败力扣题的 SQLite 题解并导入题库。"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_external_problems import (
    is_duplicate,
    load_existing_index,
    load_handwritten,
    load_solution_cache,
    process_one_slug,
    save_solution_cache,
    update_manifest,
    write_problem,
)

REPORT = ROOT / "banks" / "pta-150" / "import-external-report.json"
BANK = ROOT / "banks" / "pta-150"


def failed_slugs() -> list[str]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    added = set(report.get("added") or [])
    slugs = []
    for item in report.get("skipped_failed") or []:
        slug = item.split(":")[0].strip()
        slugs.append(slug)
    return slugs


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    slugs = failed_slugs()
    manifest_ids, existing = load_existing_index(BANK)
    load_handwritten()
    load_solution_cache()

    print(f"Backfilling {len(slugs)} failed slugs…")
    added: list[str] = []
    still_fail: list[str] = []
    t0 = time.time()

    def work(slug: str) -> tuple[str, dict | None, str]:
        return process_one_slug(slug)

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, s): s for s in slugs}
        for fut in as_completed(futs):
            slug, built, status = fut.result()
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(slugs)} ({time.time()-t0:.1f}s)")

            if status != "ok" or not built:
                still_fail.append(f"{slug}: {status}")
                continue
            dup = is_duplicate(built, existing)
            if dup:
                still_fail.append(f"{slug}: dup {dup}")
                continue
            if args.dry_run:
                added.append(built["id"])
                existing[built["id"]] = built["meta"]
                continue
            write_problem(BANK, built)
            manifest_ids.append(built["id"])
            existing[built["id"]] = built["meta"]
            added.append(built["id"])

    save_solution_cache()

    if not args.dry_run and added:
        update_manifest(BANK, manifest_ids)

    out = {
        "added": added,
        "still_failed": still_fail,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    path = BANK / "backfill-report.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nAdded {len(added)}, still failed {len(still_fail)}, {out['elapsed_sec']}s")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
