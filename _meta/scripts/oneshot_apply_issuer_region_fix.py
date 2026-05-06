#!/usr/bin/env python3
"""
oneshot: 应用 B3 issuer/region 修复(SKILL §6 重抓重入例外协议变体)

输入: _l2_rebuild_state/issuer_region_fix_output.jsonl(B3 subagent 产出)
       每行 {pid, filename, suggested_issuer, suggested_region, confidence, evidence, method}

行为(只对 confidence ≥ 0.5 的 record 应用):
1. 备份 0_raw/policies/{filename} → 0_raw/_archive/policies/{filename}__pre_issuer_fix_<ts>.md
2. 改 fm.issuer (如原 iss_unk) + fm.region (如原 reg_unk)
3. 在 fm.provenance 下加 audit 字段:
     issuer_fixed_at / issuer_fixed_method / issuer_fixed_from
     region_fixed_at / region_fixed_method / region_fixed_from
4. body 完全不动
5. 跑 deterministic post-llm 把 region 重新 crystallize
"""
from __future__ import annotations
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = VAULT / "_l2_rebuild_state" / "issuer_region_fix_output.jsonl"
RAW_DIR = VAULT / "0_raw" / "policies"
ARCHIVE_DIR = VAULT / "0_raw" / "_archive" / "policies"
NOW_ISO = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
NOW_TS = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
MIN_CONFIDENCE = 0.5
# 严格 fm 边界:^---\n ... \n---\s*(\n|$) — 防止 title 含 '---' 时把 fm 截短
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)


def parse_fm(text: str) -> tuple[dict, str, str]:
    """split frontmatter / body. return (fm_dict, fm_raw_text, body_text)
    用 line-anchored regex 找 closing ---,避免 title/value 中的 '---' 误匹配。
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, "", text
    fm_raw = m.group(1)
    body = text[m.end():]
    try:
        fm = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, fm_raw, body


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"[fatal] 缺 {INPUT_PATH}")
        return 1
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for line in INPUT_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[skip-bad-json] {e}: {line[:80]}")

    print(f"读入 {len(records)} 条建议")

    applied = 0
    skipped_low = 0
    skipped_missing = 0
    iss_changed = 0
    reg_changed = 0

    for r in records:
        pid = r.get("pid")
        fn = r.get("filename")
        conf = r.get("confidence", 0)
        if conf < MIN_CONFIDENCE:
            skipped_low += 1
            continue
        rp = RAW_DIR / fn
        if not rp.exists():
            print(f"[skip-missing] {fn}")
            skipped_missing += 1
            continue
        text = rp.read_text(encoding="utf-8")
        fm, fm_raw, body = parse_fm(text)
        if not fm:
            print(f"[skip-bad-fm] {fn}")
            skipped_missing += 1
            continue

        # 备份
        archive_name = f"{fn[:-3]}__pre_issuer_fix_{NOW_TS}.md"
        shutil.copy2(rp, ARCHIVE_DIR / archive_name)

        # 改 issuer(如原值含未知)
        cur_iss = fm.get("issuer") or []
        if isinstance(cur_iss, str):
            cur_iss = [cur_iss]
        sugg_iss = r.get("suggested_issuer") or []
        if isinstance(sugg_iss, str):
            sugg_iss = [sugg_iss]
        iss_was_unknown = "未知机构" in cur_iss or any("未知" in i for i in cur_iss)
        if iss_was_unknown and sugg_iss:
            fm["issuer"] = sugg_iss
            iss_changed += 1

        # 改 region(如原值未知)
        cur_reg = fm.get("region") or {}
        if not isinstance(cur_reg, dict):
            cur_reg = {}
        cur_rname = cur_reg.get("name", "")
        sugg_reg = r.get("suggested_region") or {}
        reg_was_unknown = cur_rname == "未知" or not cur_rname
        if reg_was_unknown and sugg_reg.get("name") and sugg_reg.get("code"):
            fm["region"] = {
                "level": sugg_reg.get("level", "未知"),
                "code": sugg_reg.get("code", "000000"),
                "name": sugg_reg.get("name", "未知"),
            }
            reg_changed += 1

        # provenance audit
        prov = fm.get("provenance") or {}
        if not isinstance(prov, dict):
            prov = {}
        if iss_was_unknown and sugg_iss:
            prov["issuer_fixed_at"] = NOW_ISO
            prov["issuer_fixed_method"] = r.get("method", "llm_body_extract")
            prov["issuer_fixed_from"] = cur_iss
            prov["issuer_fix_confidence"] = conf
        if reg_was_unknown and sugg_reg.get("name"):
            prov["region_fixed_at"] = NOW_ISO
            prov["region_fixed_method"] = r.get("method", "llm_body_extract")
            prov["region_fixed_from"] = cur_rname or "(empty)"
            prov["region_fix_confidence"] = conf
        fm["provenance"] = prov

        # 仅当真有修改时写
        if iss_was_unknown and sugg_iss or reg_was_unknown and sugg_reg.get("name"):
            new_fm_text = yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
            # body 是 m.end() 之后的内容,已包含 closing ---'s 后的 \n,不要再 prepend
            new_text = f"---\n{new_fm_text}---\n{body.lstrip(chr(10))}"
            rp.write_text(new_text, encoding="utf-8")
            applied += 1
        else:
            # 没改任何东西,删掉刚才创建的备份
            (ARCHIVE_DIR / archive_name).unlink(missing_ok=True)

    print(f"\n应用 {applied} 个 raw fm 修改:")
    print(f"  issuer 改: {iss_changed}")
    print(f"  region 改: {reg_changed}")
    print(f"  跳过(低置信 <{MIN_CONFIDENCE}): {skipped_low}")
    print(f"  跳过(缺文件 / 解析失败): {skipped_missing}")
    print(f"  备份目录: {ARCHIVE_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
