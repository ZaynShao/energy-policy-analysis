#!/usr/bin/env python3
"""一次性脚本:把 B7 isolated 分类结果落到 79 raw 政策 fm 上(SKILL §6 协议变体)

本脚本 ≠ 修 fact 字段。fm.classification + fm.tags 是 audit/分类元数据范畴
(类比 SKILL §6 协议 body_refetched_* 字段),用以让 Obsidian graph view
能基于 tag 过滤掉 79 noise 节点(`-#classified_main_graph_exclude`)。

策略:
- 源 of truth = `_meta/audit/isolated_classification.jsonl`(B7 79 行 exclude)
- 对每个 exclude 政策:
  1. 备份 raw → `0_raw/_archive/policies/{fn}__pre_classification_<ts>.md`
  2. line-anchored regex 解 fm:`^---\\s*\\n(.*?)\\n---\\s*(\\n|$)` (SKILL §6 经验)
  3. 加 fm.classification(dict)+ fm.tags(append `classified_main_graph_exclude`)
  4. fm.provenance.classification_applied_at 留时间戳(可追溯)
  5. body 一字不动

幂等:重跑不重复加 tag(检查 fm.tags 是否含 marker)。

用法:
    python3 _meta/scripts/oneshot_apply_classification_tags.py [--dry-run]
"""
import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parents[2]
POLICIES = VAULT / "0_raw" / "policies"
AUDIT_JSONL = VAULT / "_meta" / "audit" / "isolated_classification.jsonl"
ARCHIVE = VAULT / "0_raw" / "_archive" / "policies"

CST = timezone(timedelta(hours=8))
TAG_MARKER = "classified_main_graph_exclude"

# SKILL §6 + B3 经验:line-anchored,避免 title 含 --- 截断
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)


def now_iso() -> str:
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_classification() -> dict[str, dict]:
    """返回 {pid: {label, suggested_action, confidence, ...}} 仅 exclude 行"""
    if not AUDIT_JSONL.exists():
        sys.exit(f"[fatal] 缺 {AUDIT_JSONL}")
    out = {}
    for ln in AUDIT_JSONL.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("suggested_action") == "exclude_from_main_graph":
            out[r["pid"]] = r
    return out


def build_pid_to_path() -> dict[str, Path]:
    """扫 0_raw/policies/*.md → {pid: Path}"""
    out = {}
    for f in POLICIES.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        m = FM_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        pid = fm.get("id")
        if pid:
            out[pid] = f
    return out


def apply_one(path: Path, classif: dict, *, dry_run: bool, ts_safe: str) -> str:
    """单文件改 fm。返回 status: 'applied' / 'skipped_already' / 'error'"""
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return "error: no fm"
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return f"error: yaml {e}"
    body = text[m.end():]

    # 幂等检查
    existing_tags = fm.get("tags") or []
    if TAG_MARKER in existing_tags:
        return "skipped_already"

    # 加 classification dict
    fm["classification"] = {
        "isolated_label": classif["label"],
        "suggested_action": classif["suggested_action"],
        "confidence": classif.get("confidence"),
        "classified_at": classif.get("_classified_at") or now_iso(),
        "classified_by": "B7_subagent_v1",
    }
    # 加 tag(append,不覆盖)
    if not isinstance(existing_tags, list):
        existing_tags = [existing_tags] if existing_tags else []
    fm["tags"] = list(existing_tags) + [TAG_MARKER]

    # provenance.classification_applied_at(audit 字段,SKILL §6 风格)
    prov = fm.get("provenance") or {}
    if not isinstance(prov, dict):
        prov = {}
    prov["classification_applied_at"] = now_iso()
    fm["provenance"] = prov

    if dry_run:
        return "would_apply"

    # 备份(SKILL §6 协议)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    backup_name = f"{path.stem}__pre_classification_{ts_safe}.md"
    shutil.copy2(path, ARCHIVE / backup_name)

    # 序列化 fm(allow_unicode + sort_keys=False 保留键序大致)
    new_fm = yaml.safe_dump(
        fm, allow_unicode=True, default_flow_style=False, sort_keys=False
    ).rstrip()
    new_text = f"---\n{new_fm}\n---\n{body if body.startswith(chr(10)) else chr(10) + body.lstrip(chr(10))}"
    # 上面构造可能多/少一个换行,标准化:fm 后正好两个换行(--- + 空行 + body)
    new_text = re.sub(r"---\n\n+", "---\n\n", new_text, count=1)
    path.write_text(new_text, encoding="utf-8")
    return "applied"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    classification = load_classification()
    pid_to_path = build_pid_to_path()

    print(f"[load] {len(classification)} exclude pid from audit jsonl")
    print(f"[scan] {len(pid_to_path)} raw policies in 0_raw/policies/")
    print(f"[mode] {'DRY RUN' if args.dry_run else 'APPLY'}")
    print()

    ts_safe = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    counts = {"applied": 0, "would_apply": 0, "skipped_already": 0, "missing": 0, "error": 0}
    errors = []
    for pid, classif in sorted(classification.items()):
        path = pid_to_path.get(pid)
        if not path:
            counts["missing"] += 1
            errors.append(f"  [missing pid] {pid}")
            continue
        status = apply_one(path, classif, dry_run=args.dry_run, ts_safe=ts_safe)
        if status == "applied":
            counts["applied"] += 1
        elif status == "would_apply":
            counts["would_apply"] += 1
        elif status == "skipped_already":
            counts["skipped_already"] += 1
        elif status.startswith("error"):
            counts["error"] += 1
            errors.append(f"  [{status}] {pid} {path.name}")
        else:
            errors.append(f"  [unknown {status}] {pid}")

    print(f"[done] applied={counts['applied']} would={counts['would_apply']} "
          f"skipped_already={counts['skipped_already']} missing={counts['missing']} "
          f"error={counts['error']}")
    if errors:
        print("\n[errors]")
        for e in errors:
            print(e)

    if not args.dry_run and counts["applied"]:
        print(f"\nBackups → {ARCHIVE.relative_to(VAULT)}/{{pid}}__pre_classification_{ts_safe}.md")


if __name__ == "__main__":
    main()
