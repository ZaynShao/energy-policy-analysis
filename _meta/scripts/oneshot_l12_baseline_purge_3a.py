#!/usr/bin/env python3
"""
oneshot_l12_baseline_purge_3a.py — 3a: 14 评论 fm 删 LLM 派生残留字段

源:docs/handoffs/2026-05-06-baseline-l1-fm-fixes-handoff.md §3a

针对 14 篇 reclassify 时漏净化的评论(均带 _migrated_from: policies),
删除以下 5 个 LLM 派生业务字段(LLM Wiki §1 raw immutable 违规):
  - scores
  - 重要性
  - 价值标签
  - 行动分类
  - archive(派生层标记)

协议(SKILL.md §6 重抓重入例外的"轻量字段修正"分支):
  1. 备份原文件到 0_raw/_archive/commentaries/{filename}__pre_l12_purge_<ts>.md
  2. 修改 fm:删除上述字段
  3. 加 audit 字段到 provenance:
       l12_residue_purged_at: <ISO ts>
       l12_residue_purged_fields: [<deleted fields>]
  4. body 完全不动

Usage:
  python3 oneshot_l12_baseline_purge_3a.py            # dry-run (默认)
  python3 oneshot_l12_baseline_purge_3a.py --apply    # 真改 + 备份
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parents[2]
COMMENTARIES_DIR = VAULT / "0_raw" / "commentaries"
ARCHIVE_DIR = VAULT / "0_raw" / "_archive" / "commentaries"
RESIDUE_AUDIT = VAULT / "_meta" / "scripts" / "oneshot_l12_residue_audit.py"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

PURGE_FIELDS = ("scores", "重要性", "价值标签", "行动分类", "archive")

YAML_DUMP_KW = dict(allow_unicode=True, default_flow_style=False, sort_keys=False)


def now_iso_shanghai() -> str:
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.now(tz=tz).replace(microsecond=0).isoformat()


def now_filename_ts() -> str:
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.now(tz=tz).strftime("%Y%m%dT%H%M%S")


def get_target_files() -> list[Path]:
    """从 oneshot_l12_residue_audit 的 violations 列表里取 14 篇。"""
    res = subprocess.run(
        ["python3", str(RESIDUE_AUDIT), "--commentaries-only", "--json"],
        capture_output=True, check=False,
    )
    d = json.loads(res.stdout)
    rels = sorted({i["file"] for i in d.get("items", [])
                   if i["level"] == "violation" and i["code"] == "fm_forbidden_field"})
    return [VAULT / r for r in rels]


def parse_fm(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text, 0
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text, 0
    if not isinstance(fm, dict):
        return None, text, 0
    return fm, text[m.end():], m.end()


def render(fm: dict, body: str) -> str:
    return "---\n" + yaml.dump(fm, **YAML_DUMP_KW) + "---\n" + body


def purge_one(path: Path, ts_iso: str, *, apply: bool, fts: str) -> dict:
    text = path.read_text(encoding="utf-8")
    fm, body, _ = parse_fm(text)
    if fm is None:
        return {"file": str(path.relative_to(VAULT)), "ok": False, "error": "no_frontmatter"}

    deleted: list[str] = []
    for k in PURGE_FIELDS:
        if k in fm:
            deleted.append(k)
            del fm[k]

    if not deleted:
        return {"file": str(path.relative_to(VAULT)), "ok": True, "skipped": True,
                "reason": "no_forbidden_fields_present"}

    # add audit to provenance (create if absent)
    prov = fm.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
        fm["provenance"] = prov
    prov["l12_residue_purged_at"] = ts_iso
    prov["l12_residue_purged_fields"] = deleted

    new_text = render(fm, body)

    info = {
        "file": str(path.relative_to(VAULT)),
        "ok": True,
        "deleted_fields": deleted,
    }

    if apply:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = ARCHIVE_DIR / f"{path.name[:-3]}__pre_l12_purge_{fts}.md"
        # use shutil.copy2 to preserve mtime
        shutil.copy2(path, backup_path)
        path.write_text(new_text, encoding="utf-8")
        info["backup"] = str(backup_path.relative_to(VAULT))

    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="3a: 14 评论 fm 删 LLM 派生残留字段")
    ap.add_argument("--apply", action="store_true",
                    help="真改 + 备份(默认 dry-run)")
    args = ap.parse_args(argv)

    files = get_target_files()
    print(f"Target files: {len(files)}")
    if not files:
        print("(no files — residue_audit returned 0 violations)")
        return 0

    ts_iso = now_iso_shanghai()
    fts = now_filename_ts()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}  ts_iso={ts_iso}  fts={fts}")
    print(f"Backup dir: {ARCHIVE_DIR.relative_to(VAULT)}")
    print()

    n_modified = 0
    n_skipped = 0
    n_failed = 0
    for p in files:
        r = purge_one(p, ts_iso, apply=args.apply, fts=fts)
        if not r.get("ok"):
            n_failed += 1
            print(f"[FAIL] {r['file']}  {r.get('error')}")
        elif r.get("skipped"):
            n_skipped += 1
            print(f"[SKIP] {r['file']}  {r.get('reason')}")
        else:
            n_modified += 1
            tag = "[APPLIED]" if args.apply else "[WOULD-MODIFY]"
            fields_str = ", ".join(r["deleted_fields"])
            print(f"{tag} {r['file']}  delete: [{fields_str}]")

    print()
    print(f"Summary: modified={n_modified}  skipped={n_skipped}  failed={n_failed}")
    if not args.apply:
        print("(dry-run — no files written. Re-run with --apply to commit)")
    return 0 if n_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
