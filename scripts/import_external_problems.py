#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从力扣（LeetCode CN）拉取 SQL 题，配合社区题解转换为外部题库格式并去重合并。

用法:
  python scripts/import_external_problems.py --bank banks/main --dry-run --limit 5
  python scripts/import_external_problems.py --bank banks/main --workers 8
  python scripts/import_external_problems.py --bank banks/main --leetcode-only
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from leetcode_schema import prepare_leetcode_schema_statements
from mysql_compat import mysql_to_sqlite
from sql_split import split_sql

LEETCODE_GRAPHQL = "https://leetcode.cn/graphql/"
COMMUNITY_SOLUTION_BASE = (
    "https://raw.githubusercontent.com/kamyu104/LeetCode-Solutions/master/MySQL"
)
SOLUTION_CACHE = ROOT / "scripts" / "data" / "leetcode-sql-solutions.json"
HANDWRITTEN_PATH = ROOT / "scripts" / "data" / "leetcode-handwritten.json"

LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int) {
  problemsetQuestionList(categorySlug: $categorySlug, limit: $limit, skip: $skip) {
    questions {
      frontendQuestionId
      titleSlug
      title
      titleCn
      difficulty
    }
  }
}
"""

DETAIL_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    translatedTitle
    difficulty
    content
    mysqlSchemas
    exampleTestcases
    metaData
  }
}
"""

DIFF_MAP = {"Easy": "easy", "Medium": "medium", "Hard": "hard", "EASY": "easy", "MEDIUM": "medium", "HARD": "hard"}

_cache_lock = Lock()
_solution_cache: dict[str, str | None] | None = None
_handwritten_cache: dict[str, str] | None = None


def http_post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    host = "leetcode.cn" if "leetcode.cn" in url else "github.com"
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SQL-OJ/0.1",
            "Referer": f"https://{host}/",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_with_retry(url: str, payload: dict, retries: int = 2, timeout: int = 30) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            return http_post_json(url, payload, timeout=timeout)
        except Exception as exc:
            last_err = exc
            time.sleep(0.8 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def load_solution_cache() -> dict[str, str | None]:
    global _solution_cache
    if _solution_cache is not None:
        return _solution_cache
    if SOLUTION_CACHE.is_file():
        _solution_cache = json.loads(SOLUTION_CACHE.read_text(encoding="utf-8"))
    else:
        _solution_cache = {}
    return _solution_cache


def load_handwritten() -> dict[str, str]:
    global _handwritten_cache
    if _handwritten_cache is not None:
        return _handwritten_cache
    if HANDWRITTEN_PATH.is_file():
        raw = json.loads(HANDWRITTEN_PATH.read_text(encoding="utf-8"))
        _handwritten_cache = {k: v for k, v in raw.items() if isinstance(v, str) and v.strip()}
    else:
        _handwritten_cache = {}
    return _handwritten_cache


def split_solution_candidates(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    cleaned = extract_sql_from_text(text)
    parts = re.split(r";\s*(?=SELECT|WITH|DELETE|UPDATE|INSERT|CREATE)", cleaned, flags=re.I)
    parts = [p.strip().rstrip(";") for p in parts if p.strip()]
    if len(parts) <= 1:
        parts = re.split(r"\n\s*(?=SELECT|WITH|DELETE|UPDATE|INSERT|CREATE)", cleaned, flags=re.I)
        parts = [p.strip().rstrip(";") for p in parts if p.strip()]
    out: list[str] = []
    for p in parts:
        upper = p.upper()
        if upper.startswith("CREATE FUNCTION"):
            continue
        if "@" in p and "SELECT" in upper:
            continue
        out.append(p)
    return out


def pick_sqlite_solution(slug: str, schemas: list[str] | None = None) -> str | None:
    candidates: list[str] = []
    hw = load_handwritten()
    if slug in hw:
        candidates.append(hw[slug])
    cached = load_solution_cache().get(slug)
    if cached:
        candidates.extend(split_solution_candidates(cached))

    seen: set[str] = set()
    for raw in candidates:
        sql = extract_sql_from_text(raw)
        if not sql or sql in seen:
            continue
        seen.add(sql)
        sql = sql if sql.endswith(";") else sql + ";"
        if schemas:
            try:
                run_reference_sql(schemas, sql)
                return sql
            except Exception:
                continue
        return sql
    return None


def save_solution_cache() -> None:
    cache = load_solution_cache()
    SOLUTION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SOLUTION_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_sql_from_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def fetch_community_solution(slug: str) -> str | None:
    cache = load_solution_cache()
    if slug in cache:
        return cache[slug]

    url = f"{COMMUNITY_SOLUTION_BASE}/{slug}.sql"
    solution: str | None = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SQL-OJ/0.1"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        sql = extract_sql_from_text(body)
        if re.search(r"\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b", sql, re.I):
            solution = sql if sql.endswith(";") else sql + ";"
    except Exception:
        solution = None

    with _cache_lock:
        cache[slug] = solution
    return solution


def html_to_md(text: str) -> str:
    if not text:
        return ""
    s = text
    s = re.sub(r"<pre>\s*<code[^>]*>(.*?)</code>\s*</pre>", r"\n```\n\1\n```\n", s, flags=re.S | re.I)
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>\s*<p[^>]*>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", title or "")
    t = re.sub(r"[\s\-_·（）()【】\[\]《》<>「」\"'`:：,.，。!?！？]", "", t)
    return t.lower()


def run_schema(conn: sqlite3.Connection, mysql_schemas: list[str]) -> None:
    for stmt in prepare_leetcode_schema_statements(mysql_schemas):
        conn.execute(stmt)


def _adapt_reference_sql(reference_sql: str) -> str:
    sql = reference_sql.strip().rstrip(";")
    if re.search(
        r"@|TO_DAYS\s*\(|DATEDIFF\s*\(|DATE_FORMAT|YEAR\s*\(|MONTH\s*\(|ON DUPLICATE KEY|CREATE FUNCTION|IFNULL\s*\(|NOW\s*\(|TIMESTAMPDIFF|SEPARATOR|INSERT\s+IGNORE",
        sql,
        re.I,
    ):
        sql = mysql_to_sqlite(sql)
    return sql


def run_reference_sql(mysql_schemas: list[str], reference_sql: str) -> tuple[list[str], list[list]]:
    conn = sqlite3.connect(":memory:")
    try:
        run_schema(conn, mysql_schemas)
        sql = _adapt_reference_sql(reference_sql)
        last_select = None
        for stmt in split_sql(sql):
            if re.match(r"^(SELECT|WITH)", stmt, re.I):
                last_select = stmt
            elif stmt.strip():
                conn.execute(stmt)
        if not last_select:
            raise ValueError("no SELECT in reference sql")
        cur = conn.execute(last_select)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
        return cols, rows
    finally:
        conn.close()


def load_existing_index(bank: Path) -> tuple[list[str], dict[str, dict]]:
    manifest_path = bank / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ids: list[str] = manifest.get("problems") or []
    index: dict[str, dict] = {}
    for pid in ids:
        meta_path = bank / "problems" / pid / "meta.json"
        if meta_path.is_file():
            index[pid] = json.loads(meta_path.read_text(encoding="utf-8"))
    return ids, index


def is_duplicate(candidate: dict, existing: dict[str, dict]) -> str | None:
    c_source = candidate.get("source")
    c_title = normalize_title(candidate.get("title", ""))
    for meta in existing.values():
        if c_source and meta.get("source") == c_source:
            if candidate.get("externalSlug") and meta.get("externalSlug") == candidate.get("externalSlug"):
                return meta["id"]
        et = normalize_title(meta.get("title", ""))
        if c_title and et and c_title == et:
            return meta["id"]
        if c_title and et and min(len(c_title), len(et)) >= 6 and (c_title in et or et in c_title):
            return meta["id"]
    return None


def fetch_leetcode_list(limit: int) -> list[dict]:
    items: list[dict] = []
    skip = 0
    page = 50
    while len(items) < limit:
        payload = {
            "query": LIST_QUERY,
            "variables": {"categorySlug": "database", "skip": skip, "limit": min(page, limit - len(items))},
        }
        data = fetch_with_retry(LEETCODE_GRAPHQL, payload)
        batch = (data.get("data", {}) or {}).get("problemsetQuestionList", {}).get("questions") or []
        if not batch:
            break
        items.extend(batch)
        skip += len(batch)
        if len(batch) < page:
            break
    return items[:limit]


def fetch_leetcode_detail(title_slug: str) -> dict | None:
    payload = {"query": DETAIL_QUERY, "variables": {"titleSlug": title_slug}}
    data = fetch_with_retry(LEETCODE_GRAPHQL, payload)
    return data.get("data", {}).get("question")


def build_leetcode_problem(detail: dict, slug: str, solution: str) -> dict | None:
    qid = str(detail.get("questionFrontendId") or detail.get("questionId") or "")
    title = detail.get("translatedTitle") or detail.get("titleCn") or detail.get("title") or slug
    diff = DIFF_MAP.get(detail.get("difficulty") or "", "medium")

    schemas = detail.get("mysqlSchemas") or []
    if isinstance(schemas, str):
        try:
            schemas = json.loads(schemas)
        except json.JSONDecodeError:
            schemas = [schemas]
    if not schemas or not any(s and str(s).strip() for s in schemas):
        return None

    solution = extract_sql_from_text(solution)
    if not solution:
        return None

    try:
        columns, rows = run_reference_sql(schemas, solution)
    except Exception:
        return None
    if not columns:
        return None

    schema_sql = ";\n\n".join(prepare_leetcode_schema_statements(schemas)) + ";\n"
    content = html_to_md(detail.get("content") or "")
    task_md = f"{content}\n" if content else f"## 目标\n\n{title}\n"
    ref = solution if solution.endswith(";") else solution + ";"

    case = {
        "id": "1",
        "seed": "",
        "expected_columns": columns,
        "expected_rows": rows,
        "reference_sql": ref,
    }

    problem_id = f"lc-{qid.zfill(4)}-{slug}"[:80]
    meta = {
        "id": problem_id,
        "title": title,
        "difficulty": diff,
        "tags": ["LeetCode", "SQL"],
        "source": "leetcode",
        "externalId": qid,
        "externalSlug": slug,
    }
    return {
        "id": problem_id,
        "meta": meta,
        "task_md": task_md,
        "schema_sql": schema_sql,
        "cases": {"cases": [case]},
        "solution_sql": ref + "\n",
        "source": "leetcode",
        "externalSlug": slug,
        "externalId": qid,
        "title": title,
    }


def process_one_slug(slug: str) -> tuple[str, dict | None, str]:
    detail = fetch_leetcode_detail(slug)
    if not detail:
        return slug, None, "detail fetch failed"
    schemas = detail.get("mysqlSchemas") or []
    solution = pick_sqlite_solution(slug, schemas)
    if not solution:
        return slug, None, "no sqlite solution"
    built = build_leetcode_problem(detail, slug, solution)
    if not built:
        return slug, None, "build failed (schema/solution mismatch)"
    return slug, built, "ok"


def write_problem(bank: Path, problem: dict) -> None:
    dest = bank / "problems" / problem["id"]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "meta.json").write_text(json.dumps(problem["meta"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "task.md").write_text(problem["task_md"], encoding="utf-8")
    (dest / "schema.sql").write_text(problem["schema_sql"], encoding="utf-8")
    (dest / "cases.json").write_text(json.dumps(problem["cases"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if problem.get("solution_sql"):
        (dest / "solution.sql").write_text(problem["solution_sql"], encoding="utf-8")


def update_manifest(bank: Path, ids: list[str]) -> None:
    manifest_path = bank / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    name = manifest.get("name") or "SQL 题库"
    if "LeetCode" not in name:
        manifest["name"] = f"{name} + LeetCode"
    manifest["problems"] = ids
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import LeetCode SQL problems into bank")
    parser.add_argument("--bank", default=str(ROOT / "banks" / "main"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--workers", type=int, default=8, help="Concurrent fetch workers")
    parser.add_argument("--slugs", nargs="*", help="Only import these slugs (for testing)")
    args = parser.parse_args()

    bank = Path(args.bank)
    if not bank.is_dir():
        print(f"Bank not found: {bank}")
        return 1

    manifest_ids, existing = load_existing_index(bank)
    added: list[str] = []
    skipped_dup: list[str] = []
    skipped_fail: list[str] = []
    t0 = time.time()

    if args.slugs:
        slugs = list(args.slugs)
        print(f"Importing {len(slugs)} specified slugs…")
    else:
        print(f"Fetching LeetCode database list (limit={args.limit})…")
        lc_list = fetch_leetcode_list(args.limit)
        slugs = [x["titleSlug"] for x in lc_list if x.get("titleSlug")]
        print(f"  {len(slugs)} slugs to process")

    # 预过滤：已在题库中的 external slug
    existing_slugs = {
        m.get("externalSlug")
        for m in existing.values()
        if m.get("source") == "leetcode" and m.get("externalSlug")
    }
    todo = [s for s in slugs if s not in existing_slugs]
    print(f"  {len(todo)} new (skip {len(slugs) - len(todo)} already imported)")

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process_one_slug, slug): slug for slug in todo}
        for fut in as_completed(futures):
            slug, built, status = fut.result()
            done += 1
            if done % 10 == 0 or done == len(todo):
                elapsed = time.time() - t0
                print(f"  progress {done}/{len(todo)} ({elapsed:.1f}s)")

            if status != "ok" or not built:
                skipped_fail.append(f"{slug}: {status}")
                continue

            dup_id = is_duplicate(built, existing)
            if dup_id:
                skipped_dup.append(f"{built['id']} (dup of {dup_id})")
                continue

            if args.dry_run:
                added.append(built["id"])
                existing[built["id"]] = built["meta"]
                continue

            write_problem(bank, built)
            manifest_ids.append(built["id"])
            existing[built["id"]] = built["meta"]
            added.append(built["id"])

    save_solution_cache()

    report = {
        "added": added,
        "skipped_duplicate": skipped_dup,
        "skipped_failed": skipped_fail,
        "elapsed_sec": round(time.time() - t0, 1),
        "workers": args.workers,
    }
    report_path = bank / "import-external-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run and added:
        update_manifest(bank, manifest_ids)

    print(f"\nDone in {report['elapsed_sec']}s")
    print(f"Added: {len(added)}")
    print(f"Skipped (duplicate): {len(skipped_dup)}")
    print(f"Skipped (failed): {len(skipped_fail)}")
    print(f"Report: {report_path}")
    if args.dry_run:
        print("(dry-run: no problem files written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
