#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MySQL → SQLite 兼容层（判题沙箱与校验脚本共用）。"""
from __future__ import annotations

import re

_RE_LINE_COMMENT = re.compile(r"--[^\n]*")
_RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def strip_sql_comments(sql: str) -> str:
    sql = _RE_BLOCK_COMMENT.sub("", sql)
    sql = _RE_LINE_COMMENT.sub("", sql)
    return sql


def _mysql_fmt_to_sqlite(fmt: str) -> str:
    return fmt.replace("%i", "%M").replace("%s", "%S")


def adapt_mysql_ddl(sql: str) -> str:
    out = sql
    out = re.sub(r"\bUNSIGNED\b", "", out, flags=re.I)
    out = re.sub(r"\bINT\b", "INTEGER", out, flags=re.I)
    out = re.sub(r"\bBIGINT\b", "INTEGER", out, flags=re.I)
    out = re.sub(r"(?i)ENUM\s*\([^)]+\)", "TEXT", out)
    out = re.sub(r"\bVARCHAR\s*\(\s*\d+\s*\)", "TEXT", out, flags=re.I)
    out = re.sub(r"\bDECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)", "REAL", out, flags=re.I)
    out = re.sub(r"\bDOUBLE\b", "REAL", out, flags=re.I)
    out = re.sub(r"\bDATETIME\b(?!\()", "TEXT", out, flags=re.I)
    out = re.sub(r"\bAUTO_INCREMENT\b", "", out, flags=re.I)
    out = re.sub(r"ENGINE\s*=\s*\w+\b", "", out, flags=re.I)
    out = re.sub(r"DEFAULT\s+CHARSET\s*=\s*\w+\b", "", out, flags=re.I)
    out = re.sub(r"COLLATE\s+\w+[^,\n;]*", "", out, flags=re.I)
    out = re.sub(r"COMMENT\s*(?:=\s*)?'[^']*'", "", out, flags=re.I)
    out = re.sub(
        r"\bUNIQUE\s+KEY\s+(\w+)\s*\(([^)]+)\)",
        r"CONSTRAINT \1 UNIQUE (\2)",
        out,
        flags=re.I,
    )
    out = re.sub(r",\s*\)", ")", out)
    out = re.sub(
        r"(?i)DEFAULT\s+datetime\('now'\)",
        "DEFAULT CURRENT_TIMESTAMP",
        out,
    )
    return out.strip()


def _adapt_create_table(stmt: str) -> tuple[str, list[str]]:
    """提取 inline KEY，转为 CREATE INDEX。"""
    m = re.search(r"(?is)CREATE\s+TABLE\s+(\w+)", stmt)
    if not m:
        return stmt, []
    table = m.group(1)
    indexes: list[str] = []

    def key_repl(match: re.Match[str]) -> str:
        indexes.append(
            f"CREATE INDEX {match.group(1)} ON {table}({match.group(2)})"
        )
        return ""

    body = re.sub(r"(?is),\s*KEY\s+(\w+)\s*\(([^)]+)\)", key_repl, stmt)
    return body, indexes


def _rewrite_insert_select_upsert(head: str, tail: str, table: str, pk: str, insert_cols: list[str]) -> str:
    from_m = re.search(r"(?is)FROM\s+(\w+)", head)
    source = from_m.group(1) if from_m else "src"
    sel = re.search(r"(?is)SELECT\s+(.+?)\s+FROM\s+", head)
    select_exprs = [e.strip() for e in sel.group(1).split(",")] if sel else []

    insert_stmt = f"{head} WHERE {pk} NOT IN (SELECT {pk} FROM {table})"
    assigns: list[str] = []
    for part in tail.split(","):
        part = part.strip()
        expr = part
        for ins_col, sel_expr in zip(insert_cols, select_exprs):
            base = sel_expr.split(".")[-1].strip()
            sub = (
                f"(SELECT {sel_expr} FROM {source} AS s "
                f"WHERE s.{pk} = {table}.{pk})"
            )
            expr = re.sub(rf"\bexcluded\.{re.escape(ins_col)}\b", sub, expr, flags=re.I)
            expr = re.sub(rf"\bnew\.{re.escape(base)}\b", sub, expr, flags=re.I)
        assigns.append(expr)
    update_stmt = (
        f"UPDATE {table} SET {', '.join(assigns)} "
        f"WHERE {pk} IN (SELECT {pk} FROM {source})"
    )
    return f"{insert_stmt}; {update_stmt}"


def _rewrite_on_duplicate_key(sql: str) -> str:
    upper = sql.upper()
    marker = "ON DUPLICATE KEY UPDATE"
    if marker not in upper:
        return sql
    idx = upper.index(marker)
    head = sql[:idx].strip()
    tail = sql[idx + len(marker) :].strip().rstrip(";")
    m = re.search(r"(?is)INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)", head)
    if not m:
        return sql
    table = m.group(1)
    pk = m.group(2).split(",")[0].strip()
    insert_cols = [c.strip() for c in m.group(2).split(",")]
    sel = re.search(r"(?is)SELECT\s+(.+?)\s+FROM\s+", head)
    if sel:
        select_exprs = [e.strip() for e in sel.group(1).split(",")]
        for ins_col, expr in zip(insert_cols, select_exprs):
            base = expr.split(".")[-1].strip()
            tail = re.sub(
                rf"\bnew\.{re.escape(base)}\b",
                f"excluded.{ins_col}",
                tail,
                flags=re.I,
            )
        head = re.sub(r"(?is)\s+AS\s+new\b", "", head)
        return _rewrite_insert_select_upsert(head, tail, table, pk, insert_cols)
    tail = re.sub(r"(?i)\bVALUES\s*\(\s*(\w+)\s*\)", r"excluded.\1", tail)
    return f"{head} ON CONFLICT({pk}) DO UPDATE SET {tail}"


def _rewrite_update_join(sql: str) -> str:
    m = re.match(
        r"(?is)UPDATE\s+(\w+)\s+(\w+)\s+(?:INNER\s+)?JOIN\s+(\w+)\s+(\w+)\s+ON\s+(.+?)\s+SET\s+(.+)$",
        sql.strip(),
    )
    if not m:
        return sql
    table, alias, join_table, join_alias, on_clause, set_clause = m.groups()
    set_sql = re.sub(rf"\b{alias}\.", "", set_clause, flags=re.I)
    on_sql = re.sub(rf"\b{alias}\.", f"{table}.", on_clause, flags=re.I)
    return (
        f"UPDATE {table} SET {set_sql} FROM {join_table} {join_alias} "
        f"WHERE {on_sql}"
    )


def _rewrite_delete_join(sql: str) -> str:
    m = re.match(
        r"(?is)DELETE\s+(\w+)\s+FROM\s+(\w+)\s+\1\s+(JOIN.+)$",
        sql.strip(),
    )
    if not m:
        return sql
    alias, table, rest = m.groups()
    return f"DELETE FROM {table} WHERE id IN (SELECT {alias}.id FROM {table} {alias} {rest})"


def _wrap_compound_order_by(sql: str) -> str:
    if not re.search(r"\bUNION\b", sql, re.I):
        return sql
    if re.search(r"\bORDER\s+BY\b", sql, re.I) and not re.match(
        r"(?is)^\s*SELECT\s+\*\s+FROM\s+\(", sql
    ):
        m = re.match(r"(?is)^(.+?\bORDER\s+BY\b.+)$", sql.strip())
        if m:
            inner = m.group(1)
            inner = re.sub(r"\bORDER\s+BY\b", "ORDER BY", inner, count=1, flags=re.I)
            # 去掉末尾 ORDER BY，放到外层
            parts = re.split(r"(?i)\border\s+by\b", inner, maxsplit=1)
            if len(parts) == 2:
                body, order = parts
                return f"SELECT * FROM ({body.strip()}) AS _sub ORDER BY {order.strip()}"
    return sql


def normalize_mysql_dialect(sql: str) -> str:
    """LeetCode schema 常见写法 → 标准 MySQL 关键字。"""
    out = sql
    out = re.sub(
        r"(?i)\bcreate\s+table\s+if\s+not\s+exists\b",
        "CREATE TABLE IF NOT EXISTS",
        out,
    )
    out = re.sub(r"(?i)\bcreate\s+table\b", "CREATE TABLE", out)
    out = re.sub(r"(?i)\btruncate\s+table\b", "DELETE FROM", out)
    out = re.sub(r"(?i)\binsert\s+into\b", "INSERT INTO", out)
    return out


def adapt_mysql_query(sql: str) -> str:
    cleaned = normalize_mysql_dialect(strip_sql_comments(sql))
    ddl = adapt_mysql_ddl(cleaned)
    parts = []
    for stmt in ddl.split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        if re.match(r"(?is)^(CREATE\s+DATABASE|USE\s+\w+)\b", stmt):
            continue
        extra_indexes: list[str] = []
        if re.match(r"(?is)^(CREATE\s+TABLE|CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS)", stmt):
            stmt, extra_indexes = _adapt_create_table(stmt)
        out = stmt
        out = re.sub(r"(?i)\bINSERT\s+IGNORE\b", "INSERT OR IGNORE", out)
        out = re.sub(r"(?i)\bNOW\s*\(\s*\)", "datetime('now')", out)
        out = re.sub(
            r"DATE_FORMAT\s*\(\s*([^,]+?)\s*,\s*'([^']+)'\s*\)",
            lambda m: f"strftime('{_mysql_fmt_to_sqlite(m.group(2))}', {m.group(1)})",
            out,
            flags=re.I,
        )
        out = re.sub(
            r"(?i)\bYEAR\s*\(\s*([^)]+?)\s*\)",
            r"CAST(strftime('%Y', \1) AS INTEGER)",
            out,
        )
        out = re.sub(
            r"(?i)\bDATEDIFF\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
            r"CAST((julianday(\1) - julianday(\2)) AS INTEGER)",
            out,
        )
        out = re.sub(
            r"(?i)DATE_ADD\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(.+?)\s+DAY\s*\)",
            r"date(\1, '+' || \2 || ' day')",
            out,
        )
        out = re.sub(
            r"(?i)DATE_SUB\s*\(\s*([^,]+?)\s*,\s*INTERVAL\s+(.+?)\s+DAY\s*\)",
            r"date(\1, '-' || \2 || ' day')",
            out,
        )
        out = re.sub(
            r"(?i)(\w+(?:\.\w+)?)\s*-\s*INTERVAL\s+(.+?)\s+DAY",
            r"date(\1, '-' || \2 || ' day')",
            out,
        )
        out = re.sub(
            r"(?i)TIMESTAMPDIFF\s*\(\s*MINUTE\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
            r"CAST((strftime('%s', \2) - strftime('%s', \1)) / 60 AS INTEGER)",
            out,
        )

        def _field_repl(m: re.Match[str]) -> str:
            col = m.group(1).strip()
            vals = [v.strip().strip("'\"") for v in m.group(2).split(",")]
            parts = [f"WHEN {col} = '{v}' THEN {i + 1}" for i, v in enumerate(vals)]
            return f"(CASE {' '.join(parts)} ELSE 0 END)"

        out = re.sub(
            r"(?i)\bFIELD\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)",
            _field_repl,
            out,
        )
        out = re.sub(
            r"(?i)GROUP_CONCAT\s*\(\s*(.+?)\s+ORDER\s+BY\s+.+?\s+SEPARATOR\s+'([^']*)'\s*\)",
            r"GROUP_CONCAT(\1, '\2')",
            out,
            flags=re.S,
        )
        out = re.sub(
            r"(?i)>\s*ALL\s*\(\s*SELECT\s+(\w+)\s+FROM\s+([^)]+?)\)",
            r"> (SELECT MAX(\1) FROM \2)",
            out,
            flags=re.S,
        )
        out = re.sub(r"(?i)VALUES\s*\(\s*(\w+)\s*\)", r"excluded.\1", out)
        out = _rewrite_on_duplicate_key(out)
        out = _rewrite_update_join(out)
        out = _rewrite_delete_join(out)
        out = _wrap_compound_order_by(out)
        parts.append(out.strip())
        parts.extend(extra_indexes)
    return "; ".join(parts)


def mysql_to_sqlite(sql: str) -> str:
    """Schema / seed / 用户 SQL 统一入口。"""
    return adapt_mysql_query(sql)


def append_verify_select(reference_sql: str, expected_columns: list[str]) -> str:
    """DML 题：reference 无 SELECT 时追加验证查询。"""
    cleaned = strip_sql_comments(reference_sql)
    if re.search(r"\b(SELECT|WITH)\b", cleaned, re.I):
        return reference_sql
    if not expected_columns:
        return reference_sql
    cols = ", ".join(expected_columns)
    return f"{reference_sql.rstrip(';')}; SELECT {cols} FROM _verify_table LIMIT 0"
