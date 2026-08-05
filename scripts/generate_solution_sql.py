#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 cases.json 第一个测试点的 reference_sql 批量生成 solution.sql。

用法:
  python scripts/generate_solution_sql.py
  python scripts/generate_solution_sql.py --bank banks/main --write
  python scripts/generate_solution_sql.py --write --force
  python scripts/generate_solution_sql.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ProblemReport:
    problem_id: str
    status: str
    message: str
    source_case_id: str | None = None


def pick_reference_sql(cases: list[dict]) -> tuple[str, str] | None:
    """优先取 id=1 的 reference_sql，否则取首个非空 reference_sql。"""
    if not cases:
        return None

    by_id = {str(c.get("id", "")): c for c in cases}
    ordered: list[dict] = []
    if "1" in by_id:
        ordered.append(by_id["1"])
    ordered.extend(c for c in cases if c is not by_id.get("1"))

    for case in ordered:
        ref = (case.get("reference_sql") or "").strip()
        if ref:
            return ref, str(case.get("id", "?"))
    return None


def generate_solutions(
    bank: Path,
    write: bool,
    force: bool,
) -> dict:
    problems_dir = bank / "problems"
    if not problems_dir.is_dir():
        raise FileNotFoundError(f"题库目录不存在: {problems_dir}")

    reports: list[ProblemReport] = []
    created = 0
    updated = 0
    skipped = 0

    for prob_dir in sorted(problems_dir.iterdir()):
        if not prob_dir.is_dir():
            continue

        slug = prob_dir.name
        cases_path = prob_dir / "cases.json"
        solution_path = prob_dir / "solution.sql"

        if not cases_path.exists():
            reports.append(ProblemReport(slug, "skip", "缺少 cases.json"))
            skipped += 1
            continue

        try:
            cases_doc = json.loads(cases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            reports.append(ProblemReport(slug, "error", f"cases.json 解析失败: {e}"))
            skipped += 1
            continue

        picked = pick_reference_sql(cases_doc.get("cases", []))
        if not picked:
            reports.append(ProblemReport(slug, "skip", "无 reference_sql"))
            skipped += 1
            continue

        ref_sql, case_id = picked
        content = ref_sql.rstrip() + "\n"

        if solution_path.exists() and not force:
            existing = solution_path.read_text(encoding="utf-8").strip()
            if existing == content.strip():
                reports.append(
                    ProblemReport(slug, "unchanged", "solution.sql 已存在且一致", case_id)
                )
            else:
                reports.append(
                    ProblemReport(
                        slug,
                        "skip",
                        "solution.sql 已存在（内容不同，使用 --force 覆盖）",
                        case_id,
                    )
                )
            skipped += 1
            continue

        existed = solution_path.exists()
        if write:
            solution_path.write_text(content, encoding="utf-8", newline="\n")
            if existed:
                updated += 1
                reports.append(
                    ProblemReport(slug, "updated", "已覆盖 solution.sql", case_id)
                )
            else:
                created += 1
                reports.append(
                    ProblemReport(slug, "created", "已生成 solution.sql", case_id)
                )
        else:
            action = "would_update" if existed else "would_create"
            reports.append(ProblemReport(slug, action, "预览（未写入）", case_id))
            if existed:
                updated += 1
            else:
                created += 1

    summary = {
        "bank": str(bank),
        "write": write,
        "force": force,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "reports": [asdict(r) for r in reports],
    }

    report_path = bank / "generate-solution-report.json"
    if write:
        report_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="从 reference_sql 批量生成 solution.sql")
    parser.add_argument("--bank", default=str(ROOT / "banks" / "main"))
    parser.add_argument(
        "--write",
        action="store_true",
        help="写入 solution.sql（默认仅预览）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的 solution.sql",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="同默认：只预览不写入",
    )
    args = parser.parse_args()

    bank = Path(args.bank)
    write = args.write and not args.dry_run

    try:
        summary = generate_solutions(bank, write=write, force=args.force)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    mode = "写入" if write else "预览"
    print(
        f"{mode}完成: 新建 {summary['created']}, "
        f"更新 {summary['updated']}, 跳过 {summary['skipped']}"
    )
    if write:
        print(f"报告: {bank / 'generate-solution-report.json'}")

    errors = [r for r in summary["reports"] if r["status"] == "error"]
    if errors:
        for item in errors:
            print(f"  ERROR {item['problem_id']}: {item['message']}", file=sys.stderr)
        sys.exit(1)

    if not write:
        print("提示: 添加 --write 以实际生成文件")


if __name__ == "__main__":
    main()
