#!/usr/bin/env python3
"""Validate handwritten LeetCode SQLite solutions against schemas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_external_problems import fetch_leetcode_detail, load_handwritten, run_reference_sql

HW = load_handwritten()
ok, bad = [], []
for i, (slug, sql) in enumerate(HW.items(), 1):
    try:
        d = fetch_leetcode_detail(slug)
        if not d:
            bad.append((slug, "no detail"))
            continue
        run_reference_sql(d["mysqlSchemas"], sql)
        ok.append(slug)
    except Exception as e:
        bad.append((slug, str(e)[:80]))
    if i % 20 == 0:
        print(f"  checked {i}/{len(HW)}", flush=True)

print(f"OK: {len(ok)}/{len(HW)}")
for slug, err in bad[:30]:
    print(f"  FAIL {slug}: {err}")
if len(bad) > 30:
    print(f"  ... and {len(bad)-30} more")

Path(ROOT / "scripts" / "data" / "handwritten-validate-report.json").write_text(
    json.dumps({"ok": ok, "failed": bad}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
