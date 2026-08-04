#!/usr/bin/env python3
"""Fix common SQLite issues in handwritten solutions and re-validate."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from import_external_problems import fetch_leetcode_detail, load_handwritten, run_reference_sql

PATH = ROOT / "scripts" / "data" / "leetcode-handwritten.json"
hw = json.loads(PATH.read_text(encoding="utf-8"))

for slug, sql in list(hw.items()):
    s = sql
    s = re.sub(r"\sAS\s+'([^']+)'", r' AS "\1"', s, flags=re.I)
    s = re.sub(r"<>", "!=", s)
    if slug == "nth-highest-salary":
        s = 'SELECT (SELECT DISTINCT salary FROM Employee ORDER BY salary DESC LIMIT 1 OFFSET 1) AS "getNthHighestSalary(2)";'
    hw[slug] = s

PATH.write_text(json.dumps(hw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ok, bad = [], []
for slug, sql in hw.items():
    try:
        d = fetch_leetcode_detail(slug)
        if not d:
            bad.append((slug, "no detail"))
            continue
        run_reference_sql(d["mysqlSchemas"], sql)
        ok.append(slug)
    except Exception as e:
        bad.append((slug, str(e)[:100]))

print(f"After fix: OK {len(ok)}/{len(hw)}, failed {len(bad)}")
for slug, err in bad[:15]:
    print(f"  {slug}: {err}")
