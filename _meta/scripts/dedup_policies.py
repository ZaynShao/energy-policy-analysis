#!/usr/bin/env python3
"""
dedup_policies.py
0_raw 同文号 dedup:同 official_number 视为同政策,选 canonical,其他移到 _duplicates/。

策略:
- canonical 选择:正文最长 → 重要性最高 → pid 字典序最小(_a 优先)
- 移 dup 文件到 0_raw/_duplicates/<official_normalized>/<filename>
- canonical frontmatter 加 dup_aliases: [old_pid, ...]
- 输出 _meta/dedup_map.json (old_pid → canonical_pid)

不删除任何文件 — raw 哲学:source of truth 永远可恢复。
"""

import re
import json
import yaml
import shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
DUPLICATES = VAULT / "0_raw" / "_duplicates"
DEDUP_MAP = VAULT / "_meta" / "dedup_map.json"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def write_back(path, fm, body):
    out = "---\n" + yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---\n" + body
    path.write_text(out, encoding="utf-8")


def normalize_filename(s):
    s = s.replace("〔", "_").replace("〕", "_").replace(" ", "_")
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    return s


def normalize_official(s):
    """归一化文号:去机构前缀(部令/委令前缀)、统一括号"""
    if not s:
        return ""
    norm = (s.replace("(", "〔").replace(")", "〕")
             .replace(" ", "").replace("　", ""))
    # 去常见机构前缀:"生态环境部令第19号" → "部令第19号"
    norm = re.sub(r"^(生态环境部|住房和?城乡建设部|工业和?信息化部|国家发展和?改革委员?会|国家能源局|国务院|商务部|财政部|交通运输部|公安部|教育部|科学技术部|人力资源和?社会保障部|自然资源部|水利部|农业农村部|文化和?旅游部|国家卫生健康委员?会|国家民族事务委员?会|国家广播电视总局|国家市场监督管理总局)", "", norm)
    return norm


def url_fingerprint(url):
    """URL 归一化(去 query / fragment / 末尾斜杠)"""
    if not url:
        return ""
    u = re.sub(r"[?#].*$", "", str(url))
    u = u.rstrip("/")
    return u.lower()


def collect_groups(policies):
    """3 轮 dedup:
    R1. 文号归一化精确匹配(老规则 + 归一化)
    R2. URL 完全相同
    R3. 同 title + 同 issuer + (date ±7 天 OR 一方 body < 1500)
    """
    groups = []
    seen = set()

    # R1. 文号(归一化)
    by_official = defaultdict(list)
    for p in policies:
        norm = normalize_official(p["fm"].get("official_number", "") or "")
        if not norm:
            continue
        by_official[norm].append(p)
    for norm, ps in by_official.items():
        if len(ps) > 1:
            groups.append(("official_norm", norm, ps))
            for p in ps:
                seen.add(p["pid"])

    # R2. URL 完全相同
    by_url = defaultdict(list)
    for p in policies:
        if p["pid"] in seen:
            continue
        url = url_fingerprint((p["fm"].get("provenance") or {}).get("url", ""))
        if not url:
            continue
        by_url[url].append(p)
    for url, ps in by_url.items():
        if len(ps) > 1:
            groups.append(("url_match", url, ps))
            for p in ps:
                seen.add(p["pid"])

    # R3. 同 title + 同 issuer + (date ±7 OR body 一边 <1500)
    remaining = [p for p in policies if p["pid"] not in seen]
    title_groups = defaultdict(list)
    for p in remaining:
        title = p["fm"].get("title", "").strip()
        issuers = tuple(sorted(p["fm"].get("issuer", []) or []))
        if title and issuers:
            title_groups[(title, issuers)].append(p)

    for key, ps in title_groups.items():
        if len(ps) <= 1:
            continue
        # 同 title + 同 issuer 的多政策,看 date / body
        ps_sorted = sorted(ps, key=lambda x: -x["body_len"])
        canonical = ps_sorted[0]
        sub_dups = []
        from datetime import date as dt_date
        try:
            d_can = dt_date(int(canonical["fm"].get("date", "")[:4]),
                            int(str(canonical["fm"].get("date", ""))[5:7]),
                            int(str(canonical["fm"].get("date", ""))[8:10]))
        except (ValueError, TypeError):
            d_can = None
        for p in ps_sorted[1:]:
            try:
                d_p = dt_date(int(p["fm"].get("date", "")[:4]),
                              int(str(p["fm"].get("date", ""))[5:7]),
                              int(str(p["fm"].get("date", ""))[8:10]))
            except (ValueError, TypeError):
                d_p = None
            same_date = (d_can and d_p and abs((d_can - d_p).days) <= 7)
            shell_page = p["body_len"] < 1500 or canonical["body_len"] < 1500
            if same_date or shell_page:
                sub_dups.append(p)
        if sub_dups:
            groups.append(("title_issuer", key, [canonical] + sub_dups))
            for p in [canonical] + sub_dups:
                seen.add(p["pid"])

    return groups


def main():
    print("Scanning policies (v2 dedup: official_norm + URL + title/issuer fuzzy)...")
    all_pol = []
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_fm(text)
        if fm is None:
            continue
        all_pol.append({
            "pid": fm.get("id", ""),
            "filename": f.name,
            "path": f,
            "fm": fm,
            "body": body,
            "body_len": len(body),
            "importance": fm.get("重要性", 0) or 0,
        })

    groups = collect_groups(all_pol)
    print(f"Found {len(groups)} dup groups, {sum(len(g[2]) for g in groups)} files total")
    print()
    rule_count = defaultdict(int)
    for rule, _, _ in groups:
        rule_count[rule] += 1
    for rule, c in rule_count.items():
        print(f"  by {rule}: {c} groups")
    # 兼容老逻辑变量
    dups = {f"{rule}::{key}": ps for rule, key, ps in groups}

    DUPLICATES.mkdir(parents=True, exist_ok=True)

    # 加载 v1 已有的 dedup_map(如有),合并
    existing_map = {}
    if DEDUP_MAP.exists():
        try:
            existing = json.loads(DEDUP_MAP.read_text(encoding="utf-8"))
            existing_map = existing.get("old_to_canonical", {})
        except (json.JSONDecodeError, ValueError):
            pass

    dedup_map = dict(existing_map)
    summary = []

    for group_idx, (rule, key, files) in enumerate(groups):
        files.sort(key=lambda x: (-x["body_len"], -x["importance"], x["pid"]))
        canonical = files[0]
        dups_to_move = files[1:]

        # canonical frontmatter:append dup_aliases(保留已有)
        existing_aliases = canonical["fm"].get("dup_aliases", []) or []
        canonical["fm"]["dup_aliases"] = sorted(set(existing_aliases + [d["pid"] for d in dups_to_move]))
        canonical["fm"]["dedup_at"] = datetime.now().isoformat(timespec="seconds")
        canonical["fm"]["dedup_rule"] = rule
        write_back(canonical["path"], canonical["fm"], canonical["body"])

        # 移文件:子目录名按 rule + key
        sub_name_raw = (str(key) if isinstance(key, str) else f"{rule}_{group_idx}")[:80]
        sub_name = normalize_filename(sub_name_raw)
        if not sub_name or sub_name == "_":
            sub_name = f"{rule}_{group_idx}"
        sub = DUPLICATES / sub_name
        sub.mkdir(parents=True, exist_ok=True)

        for d in dups_to_move:
            new_path = sub / d["filename"]
            if new_path.exists():
                continue
            shutil.move(str(d["path"]), str(new_path))
            dedup_map[d["pid"]] = canonical["pid"]

        summary.append({
            "rule": rule,
            "key": str(key)[:80] if not isinstance(key, tuple) else f"{key[0][:40]} | {' / '.join(key[1])[:40]}",
            "canonical_pid": canonical["pid"],
            "canonical_filename": canonical["filename"],
            "canonical_body_len": canonical["body_len"],
            "canonical_importance": canonical["importance"],
            "dup_count": len(dups_to_move),
            "dup_pids": [d["pid"] for d in dups_to_move],
        })

    DEDUP_MAP.parent.mkdir(parents=True, exist_ok=True)
    with open(DEDUP_MAP, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_groups": len(groups),
            "total_dups_moved_this_run": sum(len(g[2]) - 1 for g in groups),
            "old_to_canonical": dedup_map,
            "canonical_summary": summary,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n=== Done ===")
    print(f"v2 new groups: {len(groups)}")
    print(f"v2 files moved this run: {sum(len(g[2]) - 1 for g in groups)}")
    print(f"Total dedup_map size (v1+v2): {len(dedup_map)}")
    print(f"Remaining in 0_raw/policies/: {len(list(POLICIES.glob('*.md')))}")
    print(f"Dedup map: {DEDUP_MAP}")
    print()
    print(f"v2 new groups by rule:")
    for s in summary:
        print(f"  [{s['rule']:15s}] {s['canonical_pid']:35s}  +{s['dup_count']}  key={s['key'][:40]}")


if __name__ == "__main__":
    main()
