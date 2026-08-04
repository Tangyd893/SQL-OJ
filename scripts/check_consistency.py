#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查外部题库与 MySQL 源库的一致性，并校验题库内部结构。

用法:
  python scripts/check_consistency.py
  python scripts/check_consistency.py --bank banks/pta-150 --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from export_mysql_bank import DB, fetch_problems, mysql_to_sqlite
from mysql_compat import strip_sql_comments
from verify_bank import verify_bank

REQUIRED_FILES = ("meta.json", "task.md", "schema.sql", "cases.json")


def norm_sql(sql: str) -> str:
    s = strip_sql_comments(sql or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


@dataclass
class Issue:
    level: str  # error | warn | info
    category: str
    problem_id: str
    message: str


@dataclass
class ConsistencyReport:
    bank: str
    mysql_available: bool
    mysql_problem_count: int
    bank_problem_count: int
    manifest_count: int
    test_cases_mysql: int
    test_cases_bank: int
    verify_passed: int
    verify_total: int
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)


def load_bank(bank: Path) -> dict[str, dict]:
    problems: dict[str, dict] = {}
    prob_root = bank / "problems"
    for d in sorted(prob_root.iterdir()):
        if not d.is_dir():
            continue
        slug = d.name
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        cases_doc = json.loads((d / "cases.json").read_text(encoding="utf-8"))
        schema = (d / "schema.sql").read_text(encoding="utf-8")
        task = (d / "task.md").read_text(encoding="utf-8")
        problems[slug] = {
            "meta": meta,
            "cases": cases_doc.get("cases", []),
            "schema_sql": schema,
            "task_md": task,
            "dir": d,
        }
    return problems


def count_mysql_cases(problems: list[dict]) -> int:
    total = 0
    for p in problems:
        for tc in p.get("test_cases") or []:
            if tc.get("judge") is False:
                continue
            if tc.get("expected") is not None:
                total += 1
    return total


def check_bank_structure(bank: Path, bank_probs: dict[str, dict], report: ConsistencyReport) -> None:
    manifest_path = bank / "manifest.json"
    if not manifest_path.exists():
        report.issues.append(Issue("error", "structure", "-", "缺少 manifest.json"))
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_ids = manifest.get("problems") or []
    report.manifest_count = len(manifest_ids)

    disk_ids = set(bank_probs.keys())
    manifest_set = set(manifest_ids)

    for pid in sorted(manifest_set - disk_ids):
        report.issues.append(Issue("error", "structure", pid, "manifest 中有但磁盘无此目录"))
    for pid in sorted(disk_ids - manifest_set):
        report.issues.append(Issue("warn", "structure", pid, "磁盘有但 manifest 未列出"))

    for pid, data in bank_probs.items():
        prob_dir = data["dir"]
        for fname in REQUIRED_FILES:
            if not (prob_dir / fname).exists():
                report.issues.append(
                    Issue("error", "structure", pid, f"缺少文件 {fname}")
                )
        meta = data["meta"]
        if meta.get("id") != pid:
            report.issues.append(
                Issue(
                    "error",
                    "structure",
                    pid,
                    f"meta.id={meta.get('id')} 与目录名不一致",
                )
            )
        cases = data["cases"]
        if not cases:
            report.issues.append(Issue("error", "structure", pid, "cases.json 为空"))
        for c in cases:
            if not c.get("expected_columns") and c.get("expected_rows"):
                report.issues.append(
                    Issue("warn", "cases", pid, f"测试点 {c.get('id')} 有行无列")
                )
            if not c.get("reference_sql"):
                report.issues.append(
                    Issue("warn", "cases", pid, f"测试点 {c.get('id')} 无 reference_sql")
                )


def check_mysql_vs_bank(
    mysql_probs: list[dict], bank_probs: dict[str, dict], report: ConsistencyReport
) -> None:
    mysql_map = {p["slug"]: p for p in mysql_probs}
    mysql_ids = set(mysql_map.keys())
    bank_ids = set(bank_probs.keys())

    report.mysql_problem_count = len(mysql_ids)
    report.bank_problem_count = len(bank_ids)
    report.test_cases_mysql = count_mysql_cases(mysql_probs)
    report.test_cases_bank = sum(len(b["cases"]) for b in bank_probs.values())

    for slug in sorted(mysql_ids - bank_ids):
        report.issues.append(Issue("error", "mysql", slug, "MySQL 有但题库缺失"))
    for slug in sorted(bank_ids - mysql_ids):
        report.issues.append(Issue("error", "mysql", slug, "题库有但 MySQL 缺失"))

    for slug in sorted(mysql_ids & bank_ids):
        mp = mysql_map[slug]
        bp = bank_probs[slug]
        meta = bp["meta"]

        if norm_text(mp.get("title", "")) != norm_text(meta.get("title", "")):
            report.issues.append(
                Issue("warn", "metadata", slug, "title 与 MySQL 不一致")
            )
        if (mp.get("difficulty") or "").lower() != (meta.get("difficulty") or "").lower():
            report.issues.append(
                Issue("warn", "metadata", slug, "difficulty 与 MySQL 不一致")
            )

        mysql_tags = sorted(mp.get("tags") or [])
        bank_tags = sorted(meta.get("tags") or [])
        if mysql_tags != bank_tags:
            report.issues.append(Issue("warn", "metadata", slug, "tags 与 MySQL 不一致"))

        mysql_schema = norm_sql(mysql_to_sqlite(mp.get("schema_sql") or ""))
        bank_schema = norm_sql(mysql_to_sqlite(bp["schema_sql"]))
        if mysql_schema != bank_schema:
            # 允许题库 schema 含额外 USE/CREATE DATABASE 注释行差异
            if mysql_schema not in bank_schema and bank_schema not in mysql_schema:
                report.issues.append(
                    Issue("warn", "schema", slug, "schema.sql 与 MySQL 不完全一致")
                )

        mysql_tc = [
            tc
            for tc in (mp.get("test_cases") or [])
            if tc.get("judge") is not False and tc.get("expected") is not None
        ]
        bank_tc = bp["cases"]
        if len(mysql_tc) != len(bank_tc):
            report.issues.append(
                Issue(
                    "error",
                    "cases",
                    slug,
                    f"测试点数量 MySQL={len(mysql_tc)} 题库={len(bank_tc)}",
                )
            )

        if not (mp.get("solution") or "").strip():
            report.issues.append(Issue("warn", "solution", slug, "MySQL 无题解"))
        elif not all(c.get("reference_sql") for c in bank_tc):
            missing = [c.get("id") for c in bank_tc if not c.get("reference_sql")]
            if missing:
                report.issues.append(
                    Issue(
                        "warn",
                        "solution",
                        slug,
                        f"缺少 reference_sql 的测试点: {','.join(map(str, missing))}",
                    )
                )


def run_check(bank: Path, run_verify: bool) -> ConsistencyReport:
    report = ConsistencyReport(
        bank=str(bank),
        mysql_available=False,
        mysql_problem_count=0,
        bank_problem_count=0,
        manifest_count=0,
        test_cases_mysql=0,
        test_cases_bank=0,
        verify_passed=0,
        verify_total=0,
    )

    if not bank.is_dir():
        report.issues.append(Issue("error", "structure", "-", f"题库目录不存在: {bank}"))
        return report

    bank_probs = load_bank(bank)
    check_bank_structure(bank, bank_probs, report)

    mysql_probs: list[dict] = []
    try:
        mysql_probs = fetch_problems()
        report.mysql_available = True
        check_mysql_vs_bank(mysql_probs, bank_probs, report)
    except Exception as e:
        report.issues.append(
            Issue("warn", "mysql", "-", f"无法连接 MySQL，跳过库对比: {e}")
        )
        report.bank_problem_count = len(bank_probs)
        report.test_cases_bank = sum(len(b["cases"]) for b in bank_probs.values())

    if run_verify:
        summary = verify_bank(bank, write_back=False, fix_expected=False)
        report.verify_passed = summary["passed"]
        report.verify_total = summary["cases"]
        if summary["failed_count"]:
            for item in summary["failed"][:20]:
                report.issues.append(
                    Issue(
                        "error",
                        "verify",
                        item["problem_id"],
                        f"测试点 #{item['case_id']}: {item['message']}",
                    )
                )
            if summary["failed_count"] > 20:
                report.issues.append(
                    Issue(
                        "info",
                        "verify",
                        "-",
                        f"另有 {summary['failed_count'] - 20} 个验证失败未列出",
                    )
                )

    return report


def print_report(report: ConsistencyReport) -> None:
    print("=" * 60)
    print("题目 / 数据库一致性检查")
    print("=" * 60)
    print(f"题库: {report.bank}")
    print(f"MySQL: {'已连接' if report.mysql_available else '未连接'}")
    if report.mysql_available:
        print(
            f"题目数: MySQL {report.mysql_problem_count} / 题库 {report.bank_problem_count} / manifest {report.manifest_count}"
        )
        print(
            f"测试点: MySQL {report.test_cases_mysql} / 题库 {report.test_cases_bank}"
        )
    else:
        print(f"题目数: 题库 {report.bank_problem_count} / manifest {report.manifest_count}")
        print(f"测试点: 题库 {report.test_cases_bank}")
    if report.verify_total:
        print(f"SQLite 验证: {report.verify_passed}/{report.verify_total} 通过")

    errors = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warn"]
    infos = [i for i in report.issues if i.level == "info"]

    print(f"\n问题: {len(errors)} 错误, {len(warns)} 警告, {len(infos)} 提示")

    if errors:
        print("\n[错误]")
        for i in errors[:30]:
            print(f"  {i.problem_id} [{i.category}] {i.message}")
    if warns:
        print("\n[警告]")
        for i in warns[:20]:
            print(f"  {i.problem_id} [{i.category}] {i.message}")
    if infos:
        print("\n[提示]")
        for i in infos:
            print(f"  {i.problem_id} [{i.category}] {i.message}")

    status = "PASS" if report.ok else "FAIL"
    print(f"\n[{status}] 一致性检查{'通过' if report.ok else '未通过'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="检查题库与 MySQL 一致性")
    parser.add_argument("--bank", default=str(ROOT / "banks" / "pta-150"))
    parser.add_argument("--no-verify", action="store_true", help="跳过 SQLite 验证")
    parser.add_argument("--json", action="store_true", help="输出 JSON 报告")
    args = parser.parse_args()

    bank = Path(args.bank)
    report = run_check(bank, run_verify=not args.no_verify)

    out_path = bank / "consistency-report.json"
    payload = {
        **{k: v for k, v in asdict(report).items() if k != "issues"},
        "ok": report.ok,
        "issues": [asdict(i) for i in report.issues],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(report)
        print(f"\n报告已写入: {out_path}")

    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
