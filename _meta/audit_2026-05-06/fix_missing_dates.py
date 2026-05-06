#!/usr/bin/env python3
"""修复 normalize 出来的 raw 中缺 date 的: 从 title / body 头 / fetched_at 推断"""
import os
import re
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "0_raw" / "policies"


def extract_date_strong(title, body, url, fetched_at):
    """更强的 date 抽取"""
    # 1. title 中的 YYYY-MM-DD / YYYY 年 MM 月 DD 日 / YYYY/MM/DD
    for src in [str(title or ""), str(body[:1500] if body else ""), str(url or "")]:
        for pat in [
            r"(\d{4})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})\s*日?",
            r"(\d{4})\s*年\s*(\d{1,2})\s*月",  # 仅年月
            r"(\d{4})年",  # 仅年
        ]:
            m = re.search(pat, src)
            if m:
                g = m.groups()
                try:
                    if len(g) >= 3:
                        y, mo, d = int(g[0]), int(g[1]), int(g[2])
                        if 2018 <= y <= 2027 and 1 <= mo <= 12 and 1 <= d <= 31:
                            return f"{y:04d}-{mo:02d}-{d:02d}"
                    elif len(g) == 2:
                        y, mo = int(g[0]), int(g[1])
                        if 2018 <= y <= 2027 and 1 <= mo <= 12:
                            return f"{y:04d}-{mo:02d}-01"
                    elif len(g) == 1:
                        y = int(g[0])
                        if 2018 <= y <= 2027:
                            return f"{y:04d}-01-01"
                except Exception:
                    pass
    # 2. fetched_at 兜底
    if fetched_at:
        try:
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(fetched_at))
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        except Exception:
            pass
    return "1900-01-01"  # 终极兜底


def main():
    fixed = 0
    skipped = 0
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".md"):
            continue
        path = RAW / fn
        try:
            content = path.read_text()
        except Exception:
            continue
        if not content.startswith("---\n"):
            continue
        try:
            end = content.index("\n---\n", 4)
            fm_str = content[4:end]
            fm = yaml.safe_load(fm_str) or {}
            body = content[end+5:]
        except Exception:
            continue
        # 只动我们这一批的(provenance.audit_run = audit_2026-05-06)
        prov = fm.get("provenance", {}) or {}
        if prov.get("audit_run") != "audit_2026-05-06":
            skipped += 1
            continue
        # 检查 date
        if fm.get("date"):
            skipped += 1
            continue
        new_date = extract_date_strong(
            fm.get("title", ""), body, prov.get("url", ""), prov.get("fetched_at", "")
        )
        fm["date"] = new_date
        new_fm_str = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
        new_content = f"---\n{new_fm_str}---\n{content[end+4:]}"
        path.write_text(new_content)
        fixed += 1

    print(f"Fixed date for {fixed} files, skipped {skipped} (audit_run mismatch or already has date)")


if __name__ == "__main__":
    main()
