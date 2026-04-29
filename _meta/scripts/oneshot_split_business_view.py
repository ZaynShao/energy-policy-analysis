#!/usr/bin/env python3
"""
oneshot_split_business_view.py — A+ 严格分层重构 历史迁移(2026-04-29 一次性)

把 _meta/business_view/{pid}.yaml 的异质字段拆到三处,把 _consolidated.json 的
march_detail 11 篇精品迁出。跑完即归档。

迁移规则:
  263 yaml 现有字段:
    - summary           → 1_extracted/policy_summaries.jsonl (key: policy_id)
    - business_tags     → _meta/business_tags_legacy.jsonl   (key: policy_id, 暂搁待 B1 任务)
    - 其他业务私有字段保留 (scores / 重要性 / 行动分类 / 价值标签 / 影响分析)

  yaml 删除:
    - summary, business_tags, sanitized_b_at

  11 篇 march_detail 精品(_consolidated.json):
    - core_in_one_line         → summaries.jsonl  summary_one_liner   (覆盖)
    - summary_2_3_lines        → summaries.jsonl  summary             (覆盖 yaml 粗版)
    - reading_value            → summaries.jsonl  reading_value       (覆盖)
    - didi_impact_in_one_line  → business_view yaml  didi_impact_one_liner (新加)
    - biz_impact (4-key)       → business_view yaml  影响分析            (覆盖三业务粗版)
    - action_recommendations   → business_view yaml  行动建议            (新加)
    - national_source          → 1_extracted/relations/derives_from.jsonl
                                 (仅 is_national_level_originated=False 写一行)

备份:/tmp/split_business_view.bak/
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
BV = VAULT / "_meta" / "business_view"
LEGACY_TAGS = VAULT / "_meta" / "business_tags_legacy.jsonl"
SUMMARIES = VAULT / "1_extracted" / "policy_summaries.jsonl"
DERIVES_FROM = VAULT / "1_extracted" / "relations" / "derives_from.jsonl"
RAW = VAULT / "0_raw" / "policies"
CONSOLIDATED = VAULT / "_meta" / "march_report_batches" / "_consolidated.json"
BACKUP = Path("/tmp/split_business_view.bak")

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SCRIPT_TAG = "_meta/scripts/oneshot_split_business_view.py"
NOW_ISO = datetime.now().isoformat(timespec="seconds")
NOW_DATE = datetime.now().strftime("%Y-%m-%d")


def build_pid_index() -> dict:
    """title / official_number → pid 用于 derives_from 解析。"""
    idx = {}
    for p in RAW.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
            m = FM_RE.match(text)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            continue
        pid = fm.get("id") or p.stem
        title = (fm.get("title") or "").strip()
        official = (fm.get("official_number") or "").strip()
        if title:
            idx.setdefault(title, pid)
        if official:
            idx.setdefault(official, pid)
    return idx


def resolve_pid(s: str, idx: dict):
    if not s or not idx:
        return None
    s = s.strip()
    if s in idx:
        return idx[s]
    for k, v in idx.items():
        if len(k) >= 6 and (k in s or s in k):
            return v
    return None


def parse_linkage_type(linkage: str) -> str | None:
    if not linkage:
        return None
    if "直接落地" in linkage:
        return "直接落地"
    if "借鉴框架" in linkage:
        return "借鉴框架"
    if "主题对应" in linkage:
        return "主题对应"
    return None


def upsert_jsonl(path: Path, key: str, row: dict):
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get(key) != row.get(key):
                rows.append(r)
    rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def step1_yaml_split(yaml_files: list[Path]) -> dict:
    """从 263 yaml 抽 summary / business_tags 出去,删原字段。"""
    stats = {"summary_migrated": 0, "tags_migrated": 0, "yaml_pruned": 0}
    for p in yaml_files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        pid = data.get("pid") or p.stem
        changed = False

        summary_val = data.pop("summary", None)
        if summary_val:
            row = {
                "policy_id": pid,
                "summary": summary_val,
                "summary_one_liner": "",
                "reading_value": "",
                "extracted_at": NOW_ISO,
                "extracted_by": SCRIPT_TAG,
                "_migrated_from": "business_view.yaml.summary",
            }
            upsert_jsonl(SUMMARIES, "policy_id", row)
            stats["summary_migrated"] += 1
            changed = True

        tags_val = data.pop("business_tags", None)
        if tags_val:
            row = {
                "policy_id": pid,
                "business_tags": tags_val,
                "extracted_at": NOW_ISO,
                "extracted_by": SCRIPT_TAG,
                "_migrated_from": "business_view.yaml.business_tags",
            }
            upsert_jsonl(LEGACY_TAGS, "policy_id", row)
            stats["tags_migrated"] += 1
            changed = True

        # 单字段元数据(已无意义)
        if "sanitized_b_at" in data:
            data.pop("sanitized_b_at")
            changed = True

        if changed:
            data["split_at"] = NOW_DATE
            p.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
            stats["yaml_pruned"] += 1
    return stats


def step2_march_upgrade(pid_index: dict) -> dict:
    """11 篇 march_detail 精品迁出到对应位置 + 升级 business_view yaml。"""
    stats = {
        "march_count": 0,
        "summaries_upgraded": 0,
        "yaml_upgraded": 0,
        "derives_written": 0,
        "national_source_skipped": 0,
    }
    if not CONSOLIDATED.exists():
        print(f"[warn] {CONSOLIDATED} 不存在,跳过 march 升级")
        return stats

    cdata = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
    march_detail = cdata.get("march_detail", [])
    stats["march_count"] = len(march_detail)

    for d in march_detail:
        pid = d.get("id")
        if not pid:
            continue

        # summaries.jsonl 用 march 精品覆盖
        row = {
            "policy_id": pid,
            "summary": d.get("summary_2_3_lines", "") or "",
            "summary_one_liner": d.get("core_in_one_line", "") or "",
            "reading_value": d.get("reading_value", "") or "",
            "extracted_at": NOW_ISO,
            "extracted_by": SCRIPT_TAG,
            "_migrated_from": "_consolidated.json.march_detail",
        }
        upsert_jsonl(SUMMARIES, "policy_id", row)
        stats["summaries_upgraded"] += 1

        # business_view yaml 升级:影响分析 / 行动建议 / didi_impact_one_liner
        bv_path = BV / f"{pid}.yaml"
        if bv_path.exists():
            existing = yaml.safe_load(bv_path.read_text(encoding="utf-8")) or {}
        else:
            existing = {"pid": pid}

        biz_impact = d.get("biz_impact") or {}
        actions = d.get("action_recommendations") or []
        didi_one = d.get("didi_impact_in_one_line", "") or ""

        if biz_impact:
            existing["影响分析"] = dict(biz_impact)
        if actions:
            existing["行动建议"] = list(actions)
        if didi_one:
            existing["didi_impact_one_liner"] = didi_one
        existing["march_upgrade_at"] = NOW_DATE

        bv_path.write_text(
            yaml.safe_dump(existing, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        stats["yaml_upgraded"] += 1

        # derives_from.jsonl
        ns = d.get("national_source") or {}
        is_origin = ns.get("is_national_level_originated", False)
        if is_origin:
            stats["national_source_skipped"] += 1
            continue

        source_title = (ns.get("national_source_id_or_title", "") or "").strip()
        linkage_raw = ns.get("linkage", "") or ""
        linkage_type = parse_linkage_type(linkage_raw)
        evidence = (ns.get("evidence", "") or "")[:300]

        if not source_title or not linkage_type:
            continue

        target_pid = resolve_pid(source_title, pid_index)
        derives_row = {
            "from": pid,
            "to": target_pid,
            "to_title": source_title,
            "rel": "derives_from",
            "linkage_type": linkage_type,
            "evidence": evidence,
            "linkage_full": linkage_raw[:200],
            "confidence": 0.85,
            "extracted_by": SCRIPT_TAG,
            "extracted_at": NOW_ISO,
            "_migrated_from": "_consolidated.json.march_detail.national_source",
        }
        upsert_jsonl(DERIVES_FROM, "from", derives_row)
        stats["derives_written"] += 1
    return stats


def main():
    sample = "--sample" in sys.argv
    no_backup = "--no-backup" in sys.argv

    if not sample and not no_backup:
        if BACKUP.exists():
            print(f"⚠️  备份已存在: {BACKUP}\n   rm -rf 后重跑")
            sys.exit(1)
        print(f"备份 {BV}{BACKUP}/business_view ...")
        shutil.copytree(BV, BACKUP / "business_view")
        if SUMMARIES.exists():
            shutil.copy2(SUMMARIES, BACKUP / "policy_summaries.jsonl.bak")
        if LEGACY_TAGS.exists():
            shutil.copy2(LEGACY_TAGS, BACKUP / "business_tags_legacy.jsonl.bak")
        if DERIVES_FROM.exists():
            shutil.copy2(DERIVES_FROM, BACKUP / "derives_from.jsonl.bak")

    yaml_files = sorted(BV.glob("*.yaml"))
    if sample:
        yaml_files = yaml_files[:3]
    print(f"\n=== Step 1: yaml 拆字段 (count={len(yaml_files)}) ===")
    s1 = step1_yaml_split(yaml_files)
    print(f"  summary 迁出  : {s1['summary_migrated']}")
    print(f"  tags    迁出  : {s1['tags_migrated']}")
    print(f"  yaml    pruned: {s1['yaml_pruned']}")

    if sample:
        print("\n[sample] 跳过 step2 (march 升级)")
        return

    print("\n=== Step 2: march_detail 11 精品迁出 + yaml 升级 ===")
    pid_index = build_pid_index()
    print(f"  pid 索引: {len(pid_index)} 条")
    s2 = step2_march_upgrade(pid_index)
    print(f"  march 总数         : {s2['march_count']}")
    print(f"  summaries upgraded : {s2['summaries_upgraded']}")
    print(f"  yaml      upgraded : {s2['yaml_upgraded']}")
    print(f"  derives_from 写入  : {s2['derives_written']}")
    print(f"  national 源头跳过  : {s2['national_source_skipped']}")

    print("\n✅ 完成")
    print(f"   summaries jsonl  : {SUMMARIES.relative_to(VAULT)}")
    print(f"   tags legacy jsonl: {LEGACY_TAGS.relative_to(VAULT)}")
    print(f"   derives_from     : {DERIVES_FROM.relative_to(VAULT)}")
    print(f"   备份             : {BACKUP}")


if __name__ == "__main__":
    main()
