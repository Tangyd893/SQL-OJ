#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DDL / DML 题的验证 SQL 构造。"""
from __future__ import annotations

import re

from mysql_compat import strip_sql_comments

INDEX_LIST_SQL = """
SELECT GROUP_CONCAT(ii.name, ',') AS columns, il.name AS index_name
FROM pragma_index_list('orders') AS il
JOIN pragma_index_info(il.name) AS ii
WHERE il.name LIKE 'idx_%'
GROUP BY il.name
ORDER BY il.name
""".strip()


def build_verify_sql(problem_id: str, case: dict, reference_sql: str) -> str | None:
    """为无 SELECT 的 reference 构造验证查询。"""
    cleaned = strip_sql_comments(reference_sql)
    if re.search(r"\b(SELECT|WITH)\b", cleaned, re.I):
        return None

    cols = case.get("expected_columns") or []
    case_id = str(case.get("id", "1"))

    # DML：UPDATE/INSERT 后查表
    if cols and re.search(r"\b(UPDATE|INSERT|DELETE)\b", cleaned, re.I):
        if re.search(r"\bCREATE\b", cleaned, re.I):
            return None
        schema_hint = case.get("schema") or ""
        m = re.search(r"CREATE\s+TABLE\s+(\w+)", schema_hint, re.I)
        if not m:
            return None
        table = m.group(1)
        col_list = ", ".join(cols)
        order = " ORDER BY id" if "id" in cols else ""
        if "product_id" in cols:
            order = " ORDER BY product_id"
        return f"SELECT {col_list} FROM {table}{order}"

    if not re.search(r"\bCREATE\b", cleaned, re.I):
        return None

    # 索引设计题
    if problem_id == "0055-index-design" and cols == ["columns", "index_name"]:
        return INDEX_LIST_SQL

    # 电商 DDL 题
    if problem_id == "0080-ddl-design-ecommerce":
        if cols == ["column_key", "column_name", "is_nullable"] and case_id == "1":
            return """
SELECT
  CASE
    WHEN p.pk > 0 THEN 'PRI'
    WHEN EXISTS (
      SELECT 1 FROM pragma_index_list('users') il
      JOIN pragma_index_info(il.name) ii ON ii.name = p.name
      WHERE il.origin = 'u'
    ) THEN 'UNI'
    ELSE ''
  END AS column_key,
  p.name AS column_name,
  CASE WHEN p."notnull" THEN 'NO' ELSE 'YES' END AS is_nullable
FROM pragma_table_info('users') AS p
WHERE p.pk > 0 OR p.name IN ('username', 'email')
ORDER BY p.cid
""".strip()
        if cols == ["table_name", "constraint_type"] and case_id == "2":
            return """
SELECT 'orders' AS table_name, 'FOREIGN KEY' AS constraint_type
FROM sqlite_master
WHERE name = 'orders' AND sql LIKE '%FOREIGN KEY%'
""".strip()
        if cols == ["column_key", "column_name", "is_nullable"] and case_id == "3":
            return """
SELECT '' AS column_key, name AS column_name,
       CASE WHEN "notnull" THEN 'NO' ELSE 'YES' END AS is_nullable
FROM pragma_table_info('order_items')
WHERE name = 'quantity'
""".strip()

    # 多表 DDL 设计题
    if problem_id == "0060-table-design" and cols == [
        "table_name",
        "constraint_name",
        "constraint_type",
    ]:
        if case_id == "1":
            return """
SELECT m.name AS table_name,
       CASE WHEN il.origin = 'pk' THEN 'PRIMARY' ELSE il.name END AS constraint_name,
       CASE il.origin
         WHEN 'pk' THEN 'PRIMARY KEY'
         WHEN 'u' THEN 'UNIQUE'
         WHEN 'c' THEN 'FOREIGN KEY'
         ELSE 'INDEX'
       END AS constraint_type
FROM sqlite_master AS m
JOIN pragma_index_list(m.name) AS il ON m.type = 'table'
WHERE m.name IN ('users','products','orders','order_items')
  AND il.name NOT LIKE 'sqlite_%'
ORDER BY m.name, il.seq
""".strip()
        if case_id == "2":
            return """
SELECT 'orders' AS table_name, 'fk_orders_user' AS constraint_name, 'FOREIGN KEY' AS constraint_type
FROM sqlite_master WHERE name = 'orders' AND instr(sql, 'fk_orders_user') > 0
UNION ALL
SELECT 'order_items', 'fk_items_order', 'FOREIGN KEY'
FROM sqlite_master WHERE name = 'order_items' AND instr(sql, 'fk_items_order') > 0
UNION ALL
SELECT 'order_items', 'fk_items_product', 'FOREIGN KEY'
FROM sqlite_master WHERE name = 'order_items' AND instr(sql, 'fk_items_product') > 0
""".strip()
        if case_id == "3":
            return """
SELECT 'users' AS table_name, il.name AS constraint_name, 'UNIQUE' AS constraint_type
FROM pragma_index_list('users') AS il
WHERE il.origin = 'u'
ORDER BY il.name
""".strip()

    return None
