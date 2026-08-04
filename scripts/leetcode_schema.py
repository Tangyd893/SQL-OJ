#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LeetCode schema 预处理：补 CREATE TABLE、修复 INSERT 未转义单引号。"""
from __future__ import annotations

import re

from mysql_compat import mysql_to_sqlite
from sql_split import split_sql


def fix_insert_apostrophes(stmt: str) -> str:
    """LeetCode 样例如 'Heart Won't Forget' → 'Heart Won''t Forget'。"""
    if not re.match(r"(?is)^insert\s+into", stmt.strip()):
        return stmt
    out: list[str] = []
    in_quote = False
    i = 0
    n = len(stmt)
    while i < n:
        ch = stmt[i]
        if ch != "'":
            out.append(ch)
            i += 1
            continue
        if not in_quote:
            in_quote = True
            out.append(ch)
            i += 1
            continue
        if i + 1 < n and stmt[i + 1] == "'":
            out.append("''")
            i += 2
            continue
        nxt = stmt[i + 1] if i + 1 < n else ""
        if not nxt or nxt in ",)\t\n ":
            in_quote = False
            out.append(ch)
            i += 1
            continue
        out.append("''")
        i += 1
    return "".join(out)


def _table_from_stmt(stmt: str) -> str | None:
    for pat in (
        r"(?is)^create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)",
        r"(?is)^truncate\s+table\s+(\w+)",
        r"(?is)^insert\s+into\s+(\w+)",
        r"(?is)^delete\s+from\s+(\w+)",
    ):
        m = re.match(pat, stmt.strip())
        if m:
            return m.group(1)
    return None


def infer_create_table(insert_stmt: str) -> str | None:
    m = re.match(
        r"(?is)insert\s+into\s+(\w+)\s*\(([^)]+)\)\s*values",
        insert_stmt.strip(),
    )
    if not m:
        return None
    table, cols_raw = m.group(1), m.group(2)
    cols = [c.strip() for c in cols_raw.split(",")]
    defs = ", ".join(f"{c} TEXT" for c in cols)
    return f"CREATE TABLE IF NOT EXISTS {table} ({defs})"


def _augment_statements(stmts: list[str]) -> list[str]:
    has_create: set[str] = set()
    for stmt in stmts:
        m = re.match(r"(?is)^create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)", stmt)
        if m:
            has_create.add(m.group(1).lower())

    needed: list[str] = []
    seen: set[str] = set()
    for stmt in stmts:
        tbl = _table_from_stmt(stmt)
        if not tbl:
            continue
        key = tbl.lower()
        if key in has_create or key in seen:
            continue
        if re.match(r"(?is)^insert\s+into", stmt):
            create = infer_create_table(stmt)
            if create:
                needed.append(create)
                seen.add(key)
                has_create.add(key)

    out: list[str] = []
    out.extend(needed)
    for stmt in stmts:
        if re.match(r"(?is)^insert\s+into", stmt):
            stmt = fix_insert_apostrophes(stmt)
        stripped = re.sub(r"(?is)^--[^\n]*\n?", "", stmt.strip()).strip()
        if re.match(r"(?is)^(create\s+database|use\s+\w+)\b", stripped):
            continue
        out.append(stmt)
    return out


def split_schema_statements(schema_text: str) -> list[str]:
    text = schema_text.strip()
    if not text:
        return []
    if ";" in text:
        return [s.strip() for s in split_sql(text) if s.strip()]
    return [s.strip() for s in re.split(r"\n\s*\n", text) if s.strip()]


def prepare_stored_schema(schema_text: str) -> list[str]:
    """对已落盘的 schema.sql 做 LeetCode 样例修复。"""
    stmts = split_schema_statements(schema_text)
    return _augment_statements(stmts)


def prepare_leetcode_schema_statements(schemas: list[str]) -> list[str]:
    """从 LeetCode mysqlSchemas 生成可执行 SQLite 语句。"""
    converted: list[str] = []
    for raw in schemas:
        if not raw or not str(raw).strip():
            continue
        for stmt in split_sql(mysql_to_sqlite(str(raw))):
            if stmt.strip():
                converted.append(stmt.strip())
    return _augment_statements(converted)


def exec_schema(conn, schema_text: str) -> None:
    for stmt in prepare_stored_schema(schema_text):
        conn.execute(stmt)
