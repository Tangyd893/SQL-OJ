#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据题解与测试点描述推导 reference_sql。"""
from __future__ import annotations

import re

DEPT_EQ = re.compile(r"(\bdept\s*=\s*['\"])([^'\"]+)(['\"])", re.I)
DEPT_NAME_EQ = re.compile(r"(\bdept_name\s*=\s*['\"])([^'\"]+)(['\"])", re.I)
TITLE_EQ = re.compile(r"(\btitle\s*=\s*['\"])([^'\"]+)(['\"])", re.I)


def _replace_first(pattern: re.Pattern[str], sql: str, value: str) -> str:
    if not pattern.search(sql):
        return sql
    return pattern.sub(rf"\1{value}\3", sql, count=1)


def derive_reference_sql(solution: str, case: dict) -> str:
    """为单个测试点生成参考 SQL。"""
    if not solution or not solution.strip():
        return solution

    desc = case.get("description") or ""
    case_id = str(case.get("id", "1"))

    # 空结果场景：替换为不存在部门
    if any(k in desc for k in ("不存在", "空数组", "没有任何", "空结果")):
        m = re.search(r"[（(]如(.+?)[）)]", desc)
        target = (m.group(1).strip() if m else "不存在部门").strip("'\"")
        sql = solution
        for pat in (DEPT_EQ, DEPT_NAME_EQ, TITLE_EQ):
            sql = _replace_first(pat, sql, target)
        return sql

    # 多部门/多场景：从描述提取查询对象
    if case_id != "1":
        m = re.search(r"查询(.+?)(?:[：:]|$)", desc)
        if m:
            target = m.group(1).strip()
            target = re.sub(r"所有员工.*", "", target).strip()
            target = re.sub(r"表.*", "", target).strip()
            if target and not target.startswith("不") and len(target) <= 12:
                sql = solution
                for pat in (DEPT_EQ, DEPT_NAME_EQ):
                    sql = _replace_first(pat, sql, target)
                return sql

    return solution
