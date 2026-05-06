#!/usr/bin/env python3
"""
oneshot_baseline_v2_to_v3_3b.py — 3b: 145 评论 fm v2 → v3 字段重命名/重构

源:docs/handoffs/2026-05-06-baseline-l1-fm-fixes-handoff.md §3b

145 篇评论(validate_l1 schema_v2_alias 警告)用 v2 schema 字段名,导致
评论侧脚本(rebuild_l2 prepare_commentary_change / aggregate_opinions /
oneshot_b3)读到空值,stance source domain 命中率被压。

字段映射(handoff §3b 表):
  url           → source_url        (顶层重命名)
  date          → date_published    (顶层重命名)
    date: '未知' → date_published: null
    date: None   → date_published: null
  source        → source_account    (顶层重命名;wewe-rss 系统标识不动)
  confidence    → provenance.confidence       (顶层 → 嵌套)
  collected_by  → provenance.collected_by     (顶层 → 嵌套)
  collected_at  → provenance.fetched_at       (顶层 → 嵌套)

额外补丁(扩展自 handoff,基于 missing_required 分析):
  对 14 已迁移评论(_migrated_from: policies):它们仅 date 一个 v2 alias,
  且 provenance.url 存在但 source_url 缺。复制 provenance.url → 顶层
  source_url,fix 掉 14 missing_required(source_url)。

协议(SKILL.md §6 重抓重入例外):
  1. 备份原文件到 0_raw/_archive/commentaries/{filename}__pre_v3_migration_<ts>.md
  2. 修改 fm:重命名 / 重定位
  3. 加 audit 字段到 provenance:
       fm_v3_migrated_at: <ISO ts>
       fm_v3_migrated_from_v2: true
  4. body 完全不动

Usage:
  python3 oneshot_baseline_v2_to_v3_3b.py            # dry-run (默认)
  python3 oneshot_baseline_v2_to_v3_3b.py --apply    # 真改 + 备份
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
VALIDATE_L1 = VAULT / "_meta" / "scripts" / "validate_l1.py"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
YAML_DUMP_KW = dict(allow_unicode=True, default_flow_style=False, sort_keys=False)

UNKNOWN_DATE_TOKENS = {"未知", "?", "unknown", "n/a", "N/A"}


def now_iso_shanghai() -> str:
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.now(tz=tz).replace(microsecond=0).isoformat()


def now_filename_ts() -> str:
    tz = _dt.timezone(_dt.timedelta(hours=8))
    return _dt.datetime.now(tz=tz).strftime("%Y%m%dT%H%M%S")


def get_target_files() -> list[Path]:
    """从 validate_l1 取所有 schema_v2_alias warn 的文件(145 篇)。"""
    res = subprocess.run(
        ["python3", str(VALIDATE_L1), "--commentaries-only", "--json"],
        capture_output=True, check=False,
    )
    d = json.loads(res.stdout)
    rels = sorted({v["file"] for v in d.get("violations", [])
                   if v["code"] == "schema_v2_alias"})
    return [VAULT / r for r in rels]


def parse_fm(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text
    if not isinstance(fm, dict):
        return None, text
    return fm, text[m.end():]


def render(fm: dict, body: str) -> str:
    return "---\n" + yaml.dump(fm, **YAML_DUMP_KW) + "---\n" + body


def normalize_date_value(val):
    """date → date_published 值的规范化。

    返回 (新值, 是否标记为 unknown)。
      - 合法 YYYY-MM-DD 字符串或 date/datetime 对象 → 原样返回
      - '未知' / None / '' / 类似占位符 → None
    """
    if val is None or val == "":
        return None, True
    if isinstance(val, (_dt.date, _dt.datetime)):
        return val, False
    if isinstance(val, str):
        s = val.strip()
        if s in UNKNOWN_DATE_TOKENS:
            return None, True
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            return s, False
        # 其他非日期 → 当作 unknown
        return None, True
    return None, True


def migrate_one(path: Path, ts_iso: str) -> tuple[dict | None, list[str]]:
    """返回 (新 fm, ops 列表)。fm None 表示无变化或解析失败。"""
    text = path.read_text(encoding="utf-8")
    fm, body = parse_fm(text)
    if fm is None:
        return None, ["error:no_frontmatter"]

    ops: list[str] = []

    # --- 1. url → source_url(顶层重命名)
    if "url" in fm and "source_url" not in fm:
        fm["source_url"] = fm.pop("url")
        ops.append("rename:url→source_url")
    elif "url" in fm and "source_url" in fm:
        # 极端 case:同时存在,优先现有 source_url,弃 url
        fm.pop("url")
        ops.append("dedup:drop_url(source_url_exists)")

    # --- 1b. 14 已迁移文件:provenance.url 存在但顶层 source_url 缺
    if "source_url" not in fm:
        prov_existing = fm.get("provenance")
        if isinstance(prov_existing, dict) and prov_existing.get("url"):
            fm["source_url"] = prov_existing["url"]
            ops.append("copy:provenance.url→source_url")

    # --- 2. date → date_published(顶层重命名 + '未知' / null 转换)
    if "date" in fm and "date_published" not in fm:
        new_val, was_unknown = normalize_date_value(fm.pop("date"))
        fm["date_published"] = new_val
        ops.append("rename:date→date_published" + ("(unknown→null)" if was_unknown else ""))

    # --- 3. source → source_account(wewe-rss 系统标识不动)
    if "source" in fm:
        src_val = fm["source"]
        if isinstance(src_val, str) and src_val.strip() == "wewe-rss":
            # 系统标识保留;不进 source_account
            ops.append("keep:source=wewe-rss")
        elif "source_account" not in fm:
            fm["source_account"] = fm.pop("source")
            ops.append("rename:source→source_account")
        else:
            # source 与 source_account 共存:保留 source_account,丢 source
            fm.pop("source")
            ops.append("dedup:drop_source(source_account_exists)")

    # --- 4. confidence / collected_by / collected_at → provenance.{...}
    prov = fm.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
        new_prov_block = True
    else:
        new_prov_block = False

    moved = False
    for old_key, new_key in (
        ("confidence", "confidence"),
        ("collected_by", "collected_by"),
        ("collected_at", "fetched_at"),
    ):
        if old_key in fm:
            value = fm.pop(old_key)
            if new_key not in prov:
                prov[new_key] = value
                ops.append(f"move:top.{old_key}→provenance.{new_key}")
            else:
                # 已存在 → 不覆盖
                ops.append(f"skip-move:top.{old_key}(provenance.{new_key}_exists)")
            moved = True

    # --- 5. audit 字段
    prov["fm_v3_migrated_at"] = ts_iso
    prov["fm_v3_migrated_from_v2"] = True
    ops.append("audit:provenance.fm_v3_migrated_*")

    if new_prov_block and (moved or "fm_v3_migrated_at" in prov):
        fm["provenance"] = prov

    if not ops:
        return None, []
    return fm, ops


def write_one(path: Path, fm: dict, fts: str) -> Path:
    """备份原 + 写入新。返回 backup 路径。"""
    text = path.read_text(encoding="utf-8")
    _, body = parse_fm(text)
    new_text = render(fm, body)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = ARCHIVE_DIR / f"{path.name[:-3]}__pre_v3_migration_{fts}.md"
    shutil.copy2(path, backup_path)
    path.write_text(new_text, encoding="utf-8")
    return backup_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="3b: 145 评论 fm v2 → v3 重命名/重构")
    ap.add_argument("--apply", action="store_true",
                    help="真改 + 备份(默认 dry-run)")
    ap.add_argument("--limit", type=int, default=None,
                    help="只处理前 N 篇(spot-check 用)")
    args = ap.parse_args(argv)

    files = get_target_files()
    if args.limit:
        files = files[:args.limit]
    print(f"Target files: {len(files)}")
    if not files:
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
    op_counter: dict[str, int] = {}
    for p in files:
        fm, ops = migrate_one(p, ts_iso)
        if fm is None and not ops:
            n_skipped += 1
            print(f"[SKIP] {p.relative_to(VAULT)}")
            continue
        if fm is None:
            n_failed += 1
            print(f"[FAIL] {p.relative_to(VAULT)}  ops={ops}")
            continue

        for op in ops:
            tag = op.split(":", 1)[0]
            op_counter[tag] = op_counter.get(tag, 0) + 1

        if args.apply:
            backup = write_one(p, fm, fts)
            print(f"[APPLIED] {p.relative_to(VAULT)}")
            print(f"          ops: {ops}")
        else:
            print(f"[WOULD-MODIFY] {p.relative_to(VAULT)}")
            print(f"               ops: {ops}")
        n_modified += 1

    print()
    print(f"Summary: modified={n_modified}  skipped={n_skipped}  failed={n_failed}")
    print(f"Op counters: {op_counter}")
    if not args.apply:
        print("(dry-run — no files written. Re-run with --apply to commit)")
    return 0 if n_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
