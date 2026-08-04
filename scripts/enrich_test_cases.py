#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 test_cases 补充 schema_sql / judge 标记（迁移用）。"""
from __future__ import annotations

import re

TUPLE_RE = re.compile(r"\(([^()]+)\)")
DATA_TUPLE_RE = re.compile(r"\((\d+[^()]*)\)")


def strip_inserts(schema_sql: str) -> str:
    cleaned = re.sub(r"INSERT\s+INTO\b[^;]*;", "", schema_sql, flags=re.I | re.S)
    return cleaned.strip()


def primary_table(schema_sql: str) -> str | None:
    m = re.search(r"CREATE TABLE\s+(\w+)", schema_sql, re.I)
    return m.group(1) if m else None


def all_tables(schema_sql: str) -> list[str]:
    return re.findall(r"CREATE TABLE\s+(\w+)", schema_sql, re.I)


def split_column_defs(body: str) -> list[str]:
    parts: list[str] = []
    buf = ""
    depth = 0
    for ch in body:
        if ch == "(":
            depth += 1
            buf += ch
        elif ch == ")":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def table_columns(schema_sql: str, table: str) -> list[str]:
    pattern = rf"CREATE TABLE\s+{re.escape(table)}\s*\("
    m = re.search(pattern, schema_sql, re.I)
    if not m:
        return []
    start = m.end()
    depth = 1
    i = start
    while i < len(schema_sql) and depth > 0:
        ch = schema_sql[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    body = schema_sql[start : i - 1]
    cols = []
    for part in split_column_defs(body):
        if not part or part.upper().startswith(
            ("PRIMARY", "KEY", "UNIQUE", "CONSTRAINT", "FOREIGN")
        ):
            continue
        name = part.split()[0].strip("`")
        cols.append(name)
    return cols


def parse_tuple_values(raw: str) -> list[str]:
    parts = []
    buf = ""
    in_str = False
    quote = ""
    for ch in raw:
        if ch in ("'", '"') and not in_str:
            in_str = True
            quote = ch
            buf += ch
        elif in_str and ch == quote and (not buf or buf[-1] != "\\"):
            in_str = False
            buf += ch
        elif ch == "," and not in_str:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def format_sql_value(v: str) -> str:
    v = v.strip()
    if v.upper() == "NULL":
        return "NULL"
    if re.match(r"^-?\d+(\.\d+)?$", v):
        return v
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        return v if v.startswith("'") else f"'{v[1:-1]}'"
    return f"'{v}'"


def data_tuples_from_desc(desc: str) -> list[str]:
    return [m.group(1) for m in DATA_TUPLE_RE.finditer(desc)]


def build_schema_from_tuples(base_schema: str, tuple_strings: list[str]) -> str | None:
    table = primary_table(base_schema)
    if not table:
        return None
    cols = table_columns(base_schema, table)
    if not cols:
        return None

    rows_sql = []
    for ts in tuple_strings:
        vals = parse_tuple_values(ts)
        if len(vals) != len(cols):
            return None
        formatted = ", ".join(format_sql_value(v) for v in vals)
        rows_sql.append(f"({formatted})")

    if not rows_sql:
        return None

    ddl = strip_inserts(base_schema)
    col_list = ", ".join(cols)
    insert = f"INSERT INTO {table} ({col_list}) VALUES\n" + ",\n".join(rows_sql) + ";"
    return ddl + "\n\n" + insert


def build_multi_table_schema(base_schema: str, desc: str) -> str | None:
    """解析「employees 为 (...), departments 为 (...)」形式。"""
    tables = all_tables(base_schema)
    if len(tables) < 2:
        return None

    segments: list[tuple[str, list[str]]] = []
    for table in tables:
        pattern = rf"{table}\s*(?:为|表为|:)\s*"
        m = re.search(pattern, desc, re.I)
        if not m:
            continue
        rest = desc[m.end() :]
        stop = len(rest)
        for other in tables:
            if other.lower() == table.lower():
                continue
            om = re.search(rf"\b{other}\b\s*(?:为|表为|:)", rest, re.I)
            if om:
                stop = min(stop, om.start())
        chunk = rest[:stop]
        tuples = data_tuples_from_desc(chunk)
        if tuples:
            segments.append((table, tuples))

    if not segments:
        return None

    ddl = strip_inserts(base_schema)
    parts = [ddl]
    for table, tuples in segments:
        cols = table_columns(base_schema, table)
        if not cols:
            return None
        rows = []
        for ts in tuples:
            vals = parse_tuple_values(ts)
            if len(vals) != len(cols):
                return None
            rows.append("(" + ", ".join(format_sql_value(v) for v in vals) + ")")
        if rows:
            col_list = ", ".join(cols)
            parts.append(
                f"INSERT INTO {table} ({col_list}) VALUES\n" + ",\n".join(rows) + ";"
            )
    if len(parts) <= 1:
        return None
    return "\n\n".join(parts)


def extract_insert_rows(base_schema: str, table: str) -> list[list[str]]:
    pattern = rf"INSERT INTO\s+{re.escape(table)}\s*\([^)]+\)\s*VALUES\s*(.+?);"
    m = re.search(pattern, base_schema, re.I | re.S)
    if not m:
        return []
    blob = m.group(1)
    rows = []
    for chunk in re.findall(r"\(([^()]+)\)", blob):
        rows.append(parse_tuple_values(chunk))
    return rows


def insert_col_names(base_schema: str, table: str) -> list[str]:
    m = re.search(rf"INSERT INTO\s+{re.escape(table)}\s*\(([^)]+)\)", base_schema, re.I)
    if not m:
        return table_columns(base_schema, table)
    return [c.strip().strip("`") for c in m.group(1).split(",")]


def build_schema_from_dept(base_schema: str, desc: str) -> str | None:
    table = primary_table(base_schema)
    if not table:
        return None
    cols = insert_col_names(base_schema, table)
    if "dept" not in cols:
        return None

    dept_idx = cols.index("dept")
    rows = extract_insert_rows(base_schema, table)
    if not rows:
        return None

    if any(k in desc for k in ("不存在", "空数组", "空结果", "没有任何")):
        ddl = strip_inserts(base_schema)
        col_list = ", ".join(cols)
        values = []
        for r in rows:
            values.append("(" + ", ".join(format_sql_value(v) for v in r) + ")")
        if not values:
            return ddl
        return ddl + f"\n\nINSERT INTO {table} ({col_list}) VALUES\n" + ",\n".join(values) + ";"

    m = re.search(r"查询(.+?)(?:[：:]|$)", desc)
    if not m:
        return None
    dept = m.group(1).strip()
    if dept.startswith("不"):
        return None
    dept = dept.replace("所有员工", "").replace("所有", "").strip()

    filtered = [r for r in rows if len(r) > dept_idx and r[dept_idx].strip("'\"") == dept]
    if not filtered:
        return None

    ddl = strip_inserts(base_schema)
    col_list = ", ".join(cols)
    values = ["(" + ", ".join(format_sql_value(v) for v in r) + ")" for r in filtered]
    return ddl + f"\n\nINSERT INTO {table} ({col_list}) VALUES\n" + ",\n".join(values) + ";"


def enrich_test_cases(data: dict) -> None:
    base = data.get("schema_sql", "")
    for tc in data.get("test_cases", []):
        if tc.get("schema_sql"):
            tc["judge"] = True
            continue
        if tc.get("id", 1) == 1:
            tc["judge"] = True
            continue

        desc = tc.get("description", "")

        multi = build_multi_table_schema(base, desc)
        if multi:
            tc["schema_sql"] = multi
            tc["judge"] = True
            continue

        tuples = data_tuples_from_desc(desc)
        if not tuples:
            tuples = [t for t in TUPLE_RE.findall(desc) if re.match(r"\d", t.strip())]
        schema = build_schema_from_tuples(base, tuples) if tuples else None
        if schema:
            tc["schema_sql"] = schema
            tc["judge"] = True
            continue

        dept_schema = build_schema_from_dept(base, desc)
        if dept_schema:
            tc["schema_sql"] = dept_schema
            tc["judge"] = True
            continue

        # 保留测试点：使用主题 schema 判题（总比丢弃好）
        tc["judge"] = True
