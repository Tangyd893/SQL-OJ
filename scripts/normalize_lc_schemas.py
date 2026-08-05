#!/usr/bin/env python3
"""Normalize all lc-* schema.sql: blank-line split + semicolons + apostrophe fix."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from leetcode_schema import prepare_stored_schema, split_schema_statements

BANK = ROOT / "banks" / "main"


def main() -> int:
    n = 0
    for prob_dir in sorted((BANK / "problems").iterdir()):
        if not prob_dir.is_dir() or not prob_dir.name.startswith("lc-"):
            continue
        path = prob_dir / "schema.sql"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        fixed = ";\n\n".join(prepare_stored_schema(text)) + ";\n"
        if fixed != text:
            path.write_text(fixed, encoding="utf-8")
            n += 1
    print(f"Normalized {n} lc schema.sql files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
