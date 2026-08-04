#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将用户 SQL 按各测试点 reference_sql 相对基准的差异做字面量替换（与 Rust sql_adapt 一致）。"""
from __future__ import annotations

import re

DEPT_EQ = re.compile(r"(?i)(\bdept\s*=\s*['\"])([^'\"]+)(['\"])")
DEPT_NAME_EQ = re.compile(r"(?i)(\bdept_name\s*=\s*['\"])([^'\"]+)(['\"])")
TITLE_EQ = re.compile(r"(?i)(\btitle\s*=\s*['\"])([^'\"]+)(['\"])")

PATTERNS = (DEPT_EQ, DEPT_NAME_EQ, TITLE_EQ)


def _extract(sql: str, pattern: re.Pattern[str]) -> str | None:
    m = pattern.search(sql or "")
    return m.group(2) if m else None


def _replace(sql: str, pattern: re.Pattern[str], from_val: str, to_val: str) -> str:
    if from_val == to_val:
        return sql

    def repl(m: re.Match[str]) -> str:
        current = m.group(2)
        if current == from_val:
            return f"{m.group(1)}{to_val}{m.group(3)}"
        return m.group(0)

    return pattern.sub(repl, sql, count=0)


def adapt_user_sql_for_case(
    user_sql: str,
    baseline_ref: str | None,
    case_ref: str | None,
) -> str:
    base = (baseline_ref or "").strip()
    case = (case_ref or "").strip()
    if not base or not case or base.lower() == case.lower():
        return user_sql

    adapted = user_sql
    for pattern in PATTERNS:
        base_val = _extract(base, pattern)
        case_val = _extract(case, pattern)
        if base_val and case_val:
            adapted = _replace(adapted, pattern, base_val, case_val)
    return adapted
