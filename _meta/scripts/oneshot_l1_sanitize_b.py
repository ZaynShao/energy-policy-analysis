#!/usr/bin/env python3
"""
oneshot_l1_sanitize_b.py — L1.2.b 摘要段 + tags 字段下沉(2026-04-29 一次性)

L1.1.b 系统解耦后,SOP 把 `## 摘要` 段(LLM 生成)和 frontmatter `tags`(LLM 推断
业务标签)从 L1 raw 下沉到派生层 _meta/business_view/{pid}.yaml。

本脚本对 L1.2 净化后的 263 篇做补刷:
  - 提取 frontmatter `tags` → business_view.yaml `business_tags`
  - 提取 body `## 摘要` 段 → business_view.yaml `summary`
  - L1 frontmatter 删 `tags`
  - L1 body 删 `## 摘要` 段(到下一个 ## 之前)

business_view yaml 已存在(L1.2 跑过),merge 字段不覆盖。

跑完即归档。备份: /tmp/l1_sanitize_b.bak/
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
RAW = VAULT / "0_raw" / "policies"
BUSINESS_VIEW = VAULT / "_meta" / "business_view"
BACKUP_DIR = Path("/tmp/l1_sanitize_b.bak")

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
H2_RE = re.compile(r"^## ", re.MULTILINE)


def cut_section(body: str, header_re: str):
    pat = re.compile(header_re, re.MULTILINE)
    m = pat.search(body)
    if not m:
        return None, body
    h2_start, h2_end = m.start(), m.end()
    next_h2 = H2_RE.search(body, h2_end)
    sec_end = next_h2.start() if next_h2 else len(body)
    section_text = body[h2_end:sec_end].strip("\n")
    return section_text, body[:h2_start] + body[sec_end:]


def collapse_blank_lines(body: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", body)


def merge_into_business_view(pid: str, new_fields: dict):
    """读已有 business_view yaml,merge 新字段不覆盖已有,写回。"""
    bv_path = BUSINESS_VIEW / f"{pid}.yaml"
    if bv_path.exists():
        existing = yaml.safe_load(bv_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {"pid": pid}
    for k, v in new_fields.items():
        if k in existing and existing[k] not in (None, "", [], {}):
            continue
        existing[k] = v
    bv_path.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def sanitize_b(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return {"path": p.name, "skipped": "no frontmatter"}
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        return {"path": p.name, "error": f"yaml parse: {e}"}

    pid = fm.get("id") or p.stem

    new_business = {}

    if "tags" in fm:
        tags_val = fm.pop("tags")
        if tags_val:
            new_business["business_tags"] = tags_val

    summary_text, body = cut_section(body, r"^## 摘要\s*$")
    if summary_text:
        new_business["summary"] = summary_text

    if new_business:
        new_business["sanitized_b_at"] = datetime.now().strftime("%Y-%m-%d")
        merge_into_business_view(pid, new_business)

    body = collapse_blank_lines(body)
    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    p.write_text(f"---\n{new_fm}---\n{body}", encoding="utf-8")

    return {
        "path": p.name,
        "pid": pid,
        "tags_migrated": "business_tags" in new_business,
        "summary_migrated": summary_text is not None,
    }


def main():
    sample = "--sample" in sys.argv

    if not sample:
        if BACKUP_DIR.exists():
            print(f"⚠️  备份已存在: {BACKUP_DIR}\n   rm -rf 后重跑")
            sys.exit(1)
        print(f"备份 {RAW} → {BACKUP_DIR} ...")
        shutil.copytree(RAW, BACKUP_DIR)

    files = sorted(RAW.glob("*.md"))
    if sample:
        files = files[:3]
    print(f"待处理: {len(files)} 篇" + (" (sample)" if sample else ""))

    results = []
    for p in files:
        try:
            results.append(sanitize_b(p))
        except Exception as e:
            results.append({"path": p.name, "error": str(e)})

    ok = sum(1 for r in results if "error" not in r and "skipped" not in r)
    err = sum(1 for r in results if "error" in r)
    skipped = sum(1 for r in results if "skipped" in r)
    summary_migrated = sum(1 for r in results if r.get("summary_migrated"))
    tags_migrated = sum(1 for r in results if r.get("tags_migrated"))

    print(f"\n✅ 完成: ok={ok} error={err} skipped={skipped}")
    print(f"   tags 迁出 (frontmatter→business_view.business_tags): {tags_migrated}/{ok}")
    print(f"   摘要段迁出 (body→business_view.summary): {summary_migrated}/{ok}")

    if err:
        print("\n=== 错误 ===")
        for r in results:
            if "error" in r:
                print(f"  {r['path']}: {r['error']}")


if __name__ == "__main__":
    main()
