#!/usr/bin/env python3
"""
oneshot_apply_5c_subagent_results.py — 接 subagent 派生结果 → split 写 3 处(2026-04-29 一次性)

输入:多个 subagent results jsonl(默认 /tmp/5c_results_*.jsonl),每行一篇政策的派生 JSON。

每行 schema(由 subagent 按新 5C prompt 产出):
{
  "pid": "P_xxx",
  "summary": "...",
  "summary_one_liner": "...",
  "reading_value": "...",
  "national_source": {is_national_level_originated, source_title, linkage_type, evidence},
  "scores": {D1..D6},
  "影响分析": {加油, 充电, 电力_储能_V2G_交易, 乡村} 或 null,
  "行动建议": [...] 或 []
}

行为:
  - business_view yaml: scores / 重要性(算)/ 行动分类(算)/ 价值标签(空)/ 影响分析 / 行动建议 — merge 不动 march 已有精品(11 篇)
  - 1_extracted/policy_summaries.jsonl: upsert by policy_id
  - 1_extracted/relations/derives_from.jsonl: upsert by from(仅省/市级派生写入)
  - march 11 篇 yaml 用 --skip-march 跳过(默认开)

跑完即归档。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
RAW = VAULT / "0_raw" / "policies"
BV = VAULT / "_meta" / "business_view"
SUMMARIES = VAULT / "1_extracted" / "policy_summaries.jsonl"
DERIVES_FROM = VAULT / "1_extracted" / "relations" / "derives_from.jsonl"
BACKLOG_DIR = VAULT / "_meta" / "backlog"
DERIVES_UNRESOLVED = BACKLOG_DIR / "derives_from_unresolved.yaml"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SCRIPT_TAG = "_meta/scripts/oneshot_apply_5c_subagent_results.py"
NOW_ISO = datetime.now().isoformat(timespec="seconds")
NOW_DATE = datetime.now().strftime("%Y-%m-%d")
MARCH_DETAIL_PIDS = {
    "P_2026_SC_0305e288", "P_2026_NPC_03132f88", "P_2026_NEA_0304ed54",
    "P_2026_NEA_0324cd2a", "P_2026_OTHER2D4E_0327e7ba", "P_2026_NX_0320e07e",
    "P_2026_SD_03271ffc", "P_2026_SH_03132bad", "P_2026_BJ_4",
    "P_2026_CQ_16", "P_2026_OTHERD5E7_03169880",
}


def _append_unresolved_backlog(rows: list[dict]) -> None:
    """把 derives_from to=null 候选增量写入 _meta/backlog/derives_from_unresolved.yaml。

    L1.3 demand-pull 自动转换:5C LLM 给的 source_title resolve 失败 → vault 缺
    上位政策 → 写 backlog,等月报 / 主题页用到时触发采集。

    backlog 结构:dict per source_title,值含 first_seen / linkage_type / pids 引用
    列表 / 引用次数。多个政策派生自同一上位文件时聚合统计(优先级排序依据)。
    """
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    if DERIVES_UNRESOLVED.exists():
        try:
            existing = yaml.safe_load(DERIVES_UNRESOLVED.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            existing = {}
    else:
        existing = {}
    if "items" not in existing:
        existing = {
            "_doc": "derives_from to=null 候选(L1.3 demand-pull 自动 backlog)",
            "_format": "key=source_title;value={first_seen, linkage_type, ref_pids[], ref_count}",
            "items": {},
        }

    for r in rows:
        title = r["source_title"]
        entry = existing["items"].get(title, {
            "first_seen": NOW_ISO,
            "linkage_type": r["linkage_type"],
            "ref_pids": [],
            "ref_count": 0,
            "evidence_sample": r.get("evidence", "")[:200],
        })
        if r["from"] not in entry["ref_pids"]:
            entry["ref_pids"].append(r["from"])
            entry["ref_count"] = len(entry["ref_pids"])
        entry["last_seen"] = NOW_ISO
        existing["items"][title] = entry

    DERIVES_UNRESOLVED.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def compute_importance(scores: dict) -> int:
    d1, d2, d3 = scores.get("D1", 0), scores.get("D2", 0), scores.get("D3", 0)
    return round(d1 * 0.4 + d2 * 0.4 + d3 * 0.2)


def compute_action(importance: int, d6: int) -> str:
    base = {5: "A", 4: "B", 3: "C", 2: "D", 1: "D", 0: "D"}.get(importance, "D")
    if d6 >= 4 and base != "A":
        return {"B": "A", "C": "B", "D": "C"}[base]
    if d6 <= 2 and base != "D":
        return {"A": "B", "B": "C", "C": "D"}[base]
    return base


def build_pid_index() -> dict:
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


def replace_jsonl_group(path: Path, group_key: str, group_value, new_rows: list):
    """删除所有 row[group_key] == group_value 的旧行,append new_rows(可多行)。
    用于 derives_from 这种"一个 from 可派生多条 to"的关系。"""
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
            if r.get(group_key) != group_value:
                rows.append(r)
    rows.extend(new_rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def merge_business_view(pid: str, fields: dict, rerun: bool = True):
    bv_path = BV / f"{pid}.yaml"
    if bv_path.exists():
        existing = yaml.safe_load(bv_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {"pid": pid}
    for k, v in fields.items():
        if not rerun and k in existing and existing[k] not in (None, "", [], {}):
            continue
        existing[k] = v
    BV.mkdir(parents=True, exist_ok=True)
    bv_path.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def apply_one(rec: dict, pid_index: dict, stats: dict, skip_march: bool = True):
    pid = rec.get("pid")
    if not pid:
        stats["error_no_pid"] += 1
        return

    if skip_march and pid in MARCH_DETAIL_PIDS:
        stats["skipped_march"] += 1
        return

    summary = rec.get("summary", "") or ""
    summary_one_liner = rec.get("summary_one_liner", "") or ""
    reading_value = rec.get("reading_value", "") or ""
    didi_impact_one_liner = rec.get("didi_impact_one_liner", "") or ""
    national_source = rec.get("national_source") or {}
    scores = rec.get("scores") or {}
    impact = rec.get("影响分析")
    actions = rec.get("行动建议") or []

    if not scores:
        stats["error_no_scores"] += 1
        return

    importance = compute_importance(scores)
    action_class = compute_action(importance, scores.get("D6", 0))

    # 1) business_view yaml
    bv_fields = {
        "scores": scores,
        "重要性": importance,
        "行动分类": action_class,
        "价值标签": [],
        "影响分析": impact,
        "行动建议": actions,
        "extracted_at": NOW_DATE,
        "extracted_by": SCRIPT_TAG,
        "extracted_model": "claude-opus-4-7-via-subagent",
    }
    if didi_impact_one_liner:
        bv_fields["didi_impact_one_liner"] = didi_impact_one_liner
    if importance < 3:
        bv_fields["archive"] = "low_score"
    merge_business_view(pid, bv_fields, rerun=True)
    stats["yaml_upgraded"] += 1

    # 2) policy_summaries.jsonl
    upsert_jsonl(
        SUMMARIES,
        "policy_id",
        {
            "policy_id": pid,
            "summary": summary,
            "summary_one_liner": summary_one_liner,
            "reading_value": reading_value,
            "extracted_at": NOW_ISO,
            "extracted_by": SCRIPT_TAG,
            "extracted_model": "claude-opus-4-7-via-subagent",
        },
    )
    stats["summaries_upgraded"] += 1

    # 3) derives_from.jsonl - 支持新版 (primary + secondary list) 和旧版 (单一 source_title) 两种 schema
    if national_source and not national_source.get("is_national_level_originated"):
        evidence = (national_source.get("evidence") or "")[:300]
        sources = []  # 收集所有 (title, linkage_type) 待 resolve

        # 新版 schema: primary_source + secondary_sources
        primary = national_source.get("primary_source")
        if primary and isinstance(primary, dict):
            t = (primary.get("title_or_official") or "").strip()
            lt = primary.get("linkage_type")
            if t and lt in ("直接落地", "借鉴框架", "主题对应"):
                sources.append((t, lt, "primary"))
        for s in (national_source.get("secondary_sources") or []):
            if not isinstance(s, dict):
                continue
            t = (s.get("title_or_official") or "").strip()
            lt = s.get("linkage_type")
            if t and lt in ("直接落地", "借鉴框架", "主题对应"):
                sources.append((t, lt, "secondary"))

        # 旧版 schema fallback: 单一 source_title + linkage_type
        if not sources:
            source_title = (national_source.get("source_title") or "").strip()
            linkage_type = national_source.get("linkage_type")
            if source_title and linkage_type in ("直接落地", "借鉴framework", "借鉴框架", "主题对应"):
                sources.append((source_title, linkage_type, "primary"))

        # resolve 每条 source 并产生多行
        new_rows = []
        unresolved = []  # to=null 的留存,后续写 backlog
        for source_title, linkage_type, role in sources:
            target_pid = resolve_pid(source_title, pid_index)
            new_rows.append({
                "from": pid,
                "to": target_pid,
                "to_title": source_title,
                "rel": "derives_from",
                "linkage_type": linkage_type,
                "role": role,  # primary / secondary
                "evidence": evidence,
                "confidence": 0.85 if role == "primary" else 0.7,
                "extracted_by": SCRIPT_TAG,
                "extracted_at": NOW_ISO,
            })
            if target_pid is None:
                unresolved.append({
                    "from": pid,
                    "source_title": source_title,
                    "linkage_type": linkage_type,
                    "role": role,
                    "evidence": evidence[:200],
                })

        if new_rows:
            # 替换该 from 的所有旧行,append 新行(支持一对多)
            replace_jsonl_group(DERIVES_FROM, "from", pid, new_rows)
            stats["derives_written"] += len(new_rows)

        # to=null 候选写入 backlog(L1.3 demand-pull 自动转换)
        if unresolved:
            _append_unresolved_backlog(unresolved)
            stats["derives_unresolved"] = stats.get("derives_unresolved", 0) + len(unresolved)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-glob", default="/tmp/5c_results_*.jsonl",
                    help="glob 读 subagent 产出 jsonl(默认 /tmp/5c_results_*.jsonl)")
    ap.add_argument("--no-skip-march", action="store_true",
                    help="不跳过 march 11 篇精品(默认跳过)")
    args = ap.parse_args()

    skip_march = not args.no_skip_march

    # 收集所有 results
    from glob import glob
    files = sorted(glob(args.input_glob))
    if not files:
        print(f"[fatal] no input files match {args.input_glob}")
        return

    all_records = []
    for f in files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[warn] {f}: bad line ({e}): {line[:80]}")
                continue
            all_records.append(rec)
    print(f"total records: {len(all_records)} from {len(files)} files")

    pid_index = build_pid_index()
    print(f"pid index: {len(pid_index)} entries")

    stats = {
        "yaml_upgraded": 0,
        "summaries_upgraded": 0,
        "derives_written": 0,
        "derives_unresolved": 0,
        "skipped_march": 0,
        "error_no_pid": 0,
        "error_no_scores": 0,
    }
    for rec in all_records:
        try:
            apply_one(rec, pid_index, stats, skip_march=skip_march)
        except Exception as e:
            print(f"[error] {rec.get('pid', '?')}: {e}")

    print("\n=== stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["derives_unresolved"] > 0:
        print(f"\n  → {stats['derives_unresolved']} 个 derives_from to=null 已写入 backlog:")
        print(f"     {DERIVES_UNRESOLVED.relative_to(VAULT)}")
        print("     (L1.3 demand-pull 候选,按 ref_count 排优先级)")


if __name__ == "__main__":
    main()
