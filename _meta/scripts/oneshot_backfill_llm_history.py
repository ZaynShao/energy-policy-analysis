#!/usr/bin/env python3
"""
oneshot: backfill stance / opinions-summary / 5C 缺审计字段历史

A1: stance_history.jsonl 加 191 评论 build_phase_legacy 履历
A2: opinions_summary_history.jsonl 加 9 主题 build_phase_legacy 履历
A3: 给 5C business_view yaml 的 10 个缺审计字段补 build_phase_legacy 标记

每个 audit 表只跑一次 backfill(已有 build_phase_legacy 行就 skip)。
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

STANCE_HISTORY = VAULT / "_meta" / "audit" / "stance_history.jsonl"
OPINIONS_SUMMARY_HISTORY = VAULT / "_meta" / "audit" / "opinions_summary_history.jsonl"


def already_backfilled(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("trigger") == "build_phase_legacy":
                return True
        except json.JSONDecodeError:
            pass
    return False


def backfill_stance() -> None:
    if already_backfilled(STANCE_HISTORY):
        print("[skip] stance_history 已 backfill")
        return
    STANCE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    # 收集 191 linked commentaries
    com_dir = VAULT / "0_raw" / "commentaries"
    cf_list = []
    for cf in com_dir.glob("*.md"):
        txt = cf.read_text(encoding="utf-8", errors="ignore")
        if not txt.startswith("---"):
            continue
        end = txt.find("---", 3)
        try:
            fm = yaml.safe_load(txt[3:end]) or {}
        except yaml.YAMLError:
            continue
        if fm.get("not_policy_related"):
            continue
        rp = fm.get("related_policy") or []
        if rp:
            cf_list.append(cf.name)
    with STANCE_HISTORY.open("a", encoding="utf-8") as fh:
        for cf in sorted(cf_list):
            fh.write(json.dumps({
                "comment_filename": cf,
                "ran_at": None,
                "trigger": "build_phase_legacy",
                "prompt_version": "unknown_legacy",
                "model": "unknown_legacy",
                "stance_pair_total": None,
                "source_hit_rate": None,
                "backfilled_at": NOW_ISO,
            }, ensure_ascii=False) + "\n")
    print(f"✓ stance_history backfilled {len(cf_list)} commentaries")


def backfill_opinions_summary() -> None:
    if already_backfilled(OPINIONS_SUMMARY_HISTORY):
        print("[skip] opinions_summary_history 已 backfill")
        return
    OPINIONS_SUMMARY_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    themes_dir = VAULT / "2_crystallized" / "themes"
    theme_names = [t.name for t in themes_dir.iterdir() if t.is_dir() and (t / "opinions-summary.md").exists()]
    with OPINIONS_SUMMARY_HISTORY.open("a", encoding="utf-8") as fh:
        for theme in sorted(theme_names):
            fh.write(json.dumps({
                "theme_dir_name": theme,
                "ran_at": None,
                "trigger": "build_phase_legacy",
                "prompt_version": "unknown_legacy",
                "model": "unknown_legacy",
                "backfilled_at": NOW_ISO,
            }, ensure_ascii=False) + "\n")
    print(f"✓ opinions_summary_history backfilled {len(theme_names)} themes")


def backfill_5c_audit_fields() -> None:
    """给 business_view yaml 缺 extracted_at/by/model 的补 build_phase_legacy"""
    bv_dir = VAULT / "_meta" / "business_view"
    fixed = 0
    for p in bv_dir.glob("*.yaml"):
        try:
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if all(d.get(k) for k in ("extracted_at", "extracted_by", "extracted_model")):
            continue
        # 缺字段 → 补 legacy 标记
        d.setdefault("extracted_at", None)
        d.setdefault("extracted_by", "unknown_legacy")
        d.setdefault("extracted_model", "unknown_legacy")
        d.setdefault("audit_backfilled_at", NOW_ISO)
        p.write_text(
            yaml.safe_dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        fixed += 1
    print(f"✓ business_view yaml audit fields backfilled: {fixed}")


def main() -> int:
    backfill_stance()
    backfill_opinions_summary()
    backfill_5c_audit_fields()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
