#!/usr/bin/env python3
"""
oneshot: B6 cleanup — 修 raw fm.date 异常(走 SKILL §6 协议)

输入: _meta/audit/dangling_scan_2026-05-06.json (前置扫描产物)

行为:
  对 future_date 类:
    1. 备份 0_raw/policies/{filename} → 0_raw/_archive/policies/{filename}__pre_date_fix_<ts>.md
    2. 抽真实日期(优先级):
       a. URL 路径模式 /(\\d{6})/t(\\d{8})_ → exact date (method=url_path_pattern)
       b. body 文号〔(\\d{4})〕 → year-01-01 (method=body_wenhao_year, 低精度)
       c. fetched_at 截前缀 → fetched date (method=fetched_at_fallback, 最低精度)
    3. 改 fm.date,加 provenance.date_fixed_at / date_fixed_method / date_fixed_from
    4. body 完全不动

  对 jsonl from/to dangling 类: 当前 0 条,无需处理
  对 1900_with_recent_fetch: 当前 0 条,无需处理
  对 dangling_wiki_in_md: 2 条都在 _meta/schema_v3.md 里是文档示例占位符
                       (P_2025_SD_xxx / P_2026_SH_xxx),不是真 dangling,不动
"""
from __future__ import annotations
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
SCAN_REPORT = VAULT / "_meta" / "audit" / "dangling_scan_2026-05-06.json"
RAW_DIR = VAULT / "0_raw" / "policies"
ARCHIVE_DIR = VAULT / "0_raw" / "_archive" / "policies"
OUT_AUDIT = VAULT / "_meta" / "audit" / "dangling_cleanup_2026-05-06.json"

NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
NOW_TS = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)
URL_DATE_RE = re.compile(r"/(\d{6})/t(\d{8})_")
BODY_WENHAO_YEAR_RE = re.compile(r"〔(\d{4})〕")
FETCHED_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def parse_fm(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_raw = m.group(1)
    body = text[m.end():]
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def derive_date(fm: dict, body: str) -> tuple[str, str]:
    """return (new_date, method). method ∈ {url_path_pattern, body_wenhao_year, fetched_at_fallback, NONE}"""
    prov = fm.get("provenance") or {}
    url = str(prov.get("url", ""))
    fetched = str(prov.get("fetched_at", ""))

    m = URL_DATE_RE.search(url)
    if m:
        d = m.group(2)
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}", "url_path_pattern"

    m = BODY_WENHAO_YEAR_RE.search(body[:3000])
    if m:
        return f"{m.group(1)}-01-01", "body_wenhao_year"

    m = FETCHED_DATE_RE.match(fetched)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "fetched_at_fallback"

    return "", "NONE"


def main() -> int:
    if not SCAN_REPORT.exists():
        print(f"[fatal] 缺扫描报告 {SCAN_REPORT}")
        return 1
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    report = json.loads(SCAN_REPORT.read_text(encoding="utf-8"))
    future_items = report["categories"]["raw_fm_date_anomaly"]["future_date"]
    print(f"待修 future_date: {len(future_items)} 条")

    audit_records = []
    fixed_count = 0
    skipped_count = 0
    method_stats = {"url_path_pattern": 0, "body_wenhao_year": 0, "fetched_at_fallback": 0, "NONE": 0}

    for item in future_items:
        pid = item["pid"]
        fn = item["filename"]
        old_date = item["date"]
        rp = RAW_DIR / fn
        if not rp.exists():
            print(f"[skip-missing] {fn}")
            skipped_count += 1
            continue
        text = rp.read_text(encoding="utf-8")
        fm, body = parse_fm(text)
        if not fm:
            print(f"[skip-bad-fm] {fn}")
            skipped_count += 1
            continue

        new_date, method = derive_date(fm, body)
        method_stats[method] += 1
        if not new_date:
            print(f"[skip-no-derive] {pid}  ({fn})")
            skipped_count += 1
            continue

        # 备份
        archive_name = f"{fn[:-3]}__pre_date_fix_{NOW_TS}.md"
        shutil.copy2(rp, ARCHIVE_DIR / archive_name)

        # 改 fm.date
        fm["date"] = new_date

        # provenance audit
        prov = fm.get("provenance") or {}
        if not isinstance(prov, dict):
            prov = {}
        prov["date_fixed_at"] = NOW_ISO
        prov["date_fixed_method"] = method
        prov["date_fixed_from"] = old_date
        fm["provenance"] = prov

        # 写回
        new_fm_text = yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
        new_text = f"---\n{new_fm_text}---\n{body.lstrip(chr(10))}"
        rp.write_text(new_text, encoding="utf-8")
        fixed_count += 1
        audit_records.append({
            "pid": pid, "filename": fn,
            "old_date": old_date, "new_date": new_date, "method": method,
            "archived_to": archive_name,
        })
        print(f"  {pid}  {old_date} → {new_date}  ({method})")

    OUT_AUDIT.write_text(
        json.dumps({
            "cleanup_at": NOW_ISO,
            "fixed_count": fixed_count, "skipped_count": skipped_count,
            "method_stats": method_stats,
            "records": audit_records,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n=== B6 cleanup 总结 ===")
    print(f"修复 future_date: {fixed_count}")
    print(f"跳过: {skipped_count}")
    print(f"方法分布: {method_stats}")
    print(f"审计报告: {OUT_AUDIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
