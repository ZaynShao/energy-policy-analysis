#!/usr/bin/env python3
"""
lint.py
L2 健康检查 — daily 与 weekly 两模式。

用法:
  python3 lint.py daily       # 跑核心 raw/extracted 一致性
  python3 lint.py weekly      # 跑 daily + 深度规则(双向反链 / 孤儿 / 实体聚类提示 / 关系方向校验)

输出:
  3_lints/daily/<YYYY-MM-DD>.md
  3_lints/weekly/<YYYY-MM-DD>.md
  累积 _review_queue.yaml(各项 review 候选)

退出码:
  0 = clean
  1 = warnings(有问题但不阻断)
  2 = errors(critical,阻断 L2 派生)
"""

import sys
import re
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict, Counter

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
COMMENTARIES = VAULT / "0_raw" / "commentaries"
EXTRACTED = VAULT / "1_extracted"
ENTITIES = EXTRACTED / "entities"
RELATIONS = EXTRACTED / "relations"
# DIFFS 路径已 deprecated(2026-05-07,SKILL §8e)
OPINIONS = EXTRACTED / "opinions"
LINTS = VAULT / "3_lints"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LEVEL_RANK = {"国家": 4, "省": 3, "市": 2, "区": 1}

REGION_CODE = {
    "全国": "000000",
    "北京市": "110000", "天津市": "120000", "河北省": "130000",
    "山西省": "140000", "内蒙古自治区": "150000",
    "辽宁省": "210000", "吉林省": "220000", "黑龙江省": "230000",
    "上海市": "310000", "江苏省": "320000", "浙江省": "330000",
    "安徽省": "340000", "福建省": "350000", "江西省": "360000",
    "山东省": "370000",
    "河南省": "410000", "湖北省": "420000", "湖南省": "430000",
    "广东省": "440000", "广西壮族自治区": "450000", "海南省": "460000",
    "重庆市": "500000", "四川省": "510000", "贵州省": "520000",
    "云南省": "530000", "西藏自治区": "540000",
    "陕西省": "610000", "甘肃省": "620000", "青海省": "630000",
    "宁夏回族自治区": "640000", "新疆维吾尔自治区": "650000",
}


# -------- helpers --------

def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def base_id(pid):
    return re.sub(r"_[a-z]$", "", pid)


def load_policies():
    out = {}
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm is None:
            continue
        pid = fm.get("id")
        if not pid:
            continue
        out[pid] = {"fm": fm, "filename": f.name, "path": f, "body_len": len(body)}
    return out


LOW_QUALITY_THRESHOLD = 3000


def check_low_quality_capture(policies):
    """body_len < 3KB 的政策标低质量(可能 L1 抓取失败,只拿到摘要/壳页)
    例如 1810 文件 2.8KB 只有摘要,需要 L1 重抓"""
    issues = []
    for pid, m in policies.items():
        body_len = m.get("body_len", 0)
        if body_len < LOW_QUALITY_THRESHOLD:
            issues.append({
                "level": "warning",
                "category": "low_quality_capture",
                "policy_id": pid,
                "body_len": body_len,
                "filename": m["filename"],
                "suggestion": "L1 可能抓取失败(摘要/壳页),建议下次 daily-scan 重抓",
            })
    return issues


def load_registry():
    p = ENTITIES / "registry.yaml"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return []
    return yaml.safe_load(parts[2]) or []


def load_relations():
    """所有关系 jsonl → list,带 rel_type"""
    out = []
    for rel in ["supersedes", "references", "clarifies", "iterates", "extends", "aligns_with", "conflicts_with"]:
        p = RELATIONS / f"{rel}.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                d["_rel_type"] = rel
                out.append(d)
    return out


# -------- checks --------

REQUIRED_POLICY_FIELDS = ["id", "title", "date", "region", "provenance"]


def check_policy_frontmatter(policies):
    """1. 必填字段齐全"""
    issues = []
    for pid, m in policies.items():
        fm = m["fm"]
        missing = [k for k in REQUIRED_POLICY_FIELDS if not fm.get(k)]
        if missing:
            issues.append({
                "level": "error",
                "category": "frontmatter_missing",
                "policy_id": pid,
                "filename": m["filename"],
                "missing": missing,
            })
        # provenance 必须是 dict
        prov = fm.get("provenance")
        if prov is not None and not isinstance(prov, dict):
            issues.append({
                "level": "error",
                "category": "provenance_not_dict",
                "policy_id": pid,
                "filename": m["filename"],
            })
        # region 必须含 level/code/name
        region = fm.get("region")
        if isinstance(region, dict):
            if not region.get("level") or not region.get("name"):
                issues.append({
                    "level": "warning",
                    "category": "region_incomplete",
                    "policy_id": pid,
                    "region": region,
                })
    return issues


def check_id_uniqueness(policies):
    """2. id 全 vault 唯一"""
    issues = []
    seen = defaultdict(list)
    for pid, m in policies.items():
        seen[pid].append(m["filename"])
    for pid, files in seen.items():
        if len(files) > 1:
            issues.append({
                "level": "error",
                "category": "id_collision",
                "policy_id": pid,
                "files": files,
            })
    return issues


def check_relations_valid(policies, relations):
    """3. 关系引用的政策必须在 raw 里存在"""
    issues = []
    pid_set = set(policies.keys())
    for r in relations:
        for side in ("from", "to"):
            ref_pid = r.get(side)
            if not ref_pid:
                issues.append({
                    "level": "error",
                    "category": "relation_missing_id",
                    "rel": r["_rel_type"],
                    "side": side,
                    "row": r,
                })
                continue
            if ref_pid not in pid_set:
                issues.append({
                    "level": "warning",
                    "category": "relation_dangling",
                    "rel": r["_rel_type"],
                    "side": side,
                    "ref_pid": ref_pid,
                    "from": r.get("from"),
                    "to": r.get("to"),
                })
    return issues


def check_region_code_consistency(policies):
    """4. region.code 与 name 一致"""
    issues = []
    for pid, m in policies.items():
        region = m["fm"].get("region") or {}
        name = region.get("name", "")
        code = str(region.get("code", "") or "")
        expected = REGION_CODE.get(name)
        if expected and code and code != expected:
            issues.append({
                "level": "warning",
                "category": "region_code_mismatch",
                "policy_id": pid,
                "name": name,
                "code": code,
                "expected": expected,
            })
    return issues


def check_entity_extraction_coverage(policies):
    """5. 抽取实体词 100% 在 registry 命中(其实是 review_queue 健康度)"""
    issues = []
    rq = ENTITIES / "_review_queue.yaml"
    if rq.exists():
        try:
            data = yaml.safe_load(rq.read_text(encoding="utf-8")) or []
            pending = [d for d in data if not d.get("processed")]
            if pending:
                issues.append({
                    "level": "info",
                    "category": "review_queue_pending",
                    "count": len(pending),
                })
        except yaml.YAMLError:
            pass

    # 零实体命中政策(信息级,不阻断)
    extr = ENTITIES / "_extractions.jsonl"
    if extr.exists():
        with_entities = set()
        with open(extr, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                with_entities.add(d["policy_id"])
        zero_hit = set(policies.keys()) - with_entities
        if zero_hit:
            issues.append({
                "level": "info",
                "category": "zero_entity_policies",
                "count": len(zero_hit),
                "sample": sorted(zero_hit)[:10],
            })
    return issues


# [DEPRECATED 2026-05-07] check_diff_coverage 已移除 — diffs/*.md 体系下架
# (22 早期 LLM 派生 + 0 消费者,SKILL §8e「派生 .md 必须有消费者」契约)


# -------- weekly extra --------

def check_orphan_canonicals(registry):
    """孤儿 canonical(无政策引用 ≥X 天)"""
    issues = []
    extr = ENTITIES / "_extractions.jsonl"
    if not extr.exists():
        return issues
    referenced = set()
    with open(extr, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            referenced.add(d["canonical_id"])
    today = date.today()
    for e in registry:
        if e["id"] in referenced:
            continue
        added = e.get("added_at")
        if isinstance(added, date):
            days = (today - added).days
        else:
            days = 0
        if days >= 30:
            issues.append({
                "level": "info",
                "category": "orphan_canonical",
                "canonical_id": e["id"],
                "canonical_name": e.get("canonical_name", ""),
                "days_orphan": days,
            })
    return issues


def check_extends_direction(relations, policies):
    """启发式 extends 方向反查(借鉴 Step 7 Agent 反馈)"""
    issues = []
    for r in relations:
        if r["_rel_type"] != "extends":
            continue
        from_pid = r["from"]
        to_pid = r["to"]
        if from_pid not in policies or to_pid not in policies:
            continue
        fm_from = policies[from_pid]["fm"]
        fm_to = policies[to_pid]["fm"]
        # 校验 1: from.date > to.date
        d1 = str(fm_from.get("date") or "")
        d2 = str(fm_to.get("date") or "")
        if d1 and d2 and d1 < d2:
            issues.append({
                "level": "warning",
                "category": "extends_date_inverted",
                "from": from_pid, "to": to_pid,
                "from_date": d1, "to_date": d2,
            })
        # 校验 2: 同级地方间不应 extends
        l1 = LEVEL_RANK.get((fm_from.get("region") or {}).get("level"), 0)
        l2 = LEVEL_RANK.get((fm_to.get("region") or {}).get("level"), 0)
        if l1 == l2 and l1 in (2, 3):  # 同省级或同市级
            issues.append({
                "level": "warning",
                "category": "extends_same_level_local",
                "from": from_pid, "to": to_pid,
                "level": l1,
            })
    return issues


def check_dup_official_number(policies):
    """同 official_number 多政策(数据重复)"""
    issues = []
    on_to_pids = defaultdict(list)
    for pid, m in policies.items():
        official = m["fm"].get("official_number") or ""
        if official:
            on_to_pids[official].append(pid)
    for official, pids in on_to_pids.items():
        # base_id 不同的算真重复(_a/_b/_c 已知 sibling 不算)
        bases = set(base_id(p) for p in pids)
        if len(bases) > 1:
            issues.append({
                "level": "warning",
                "category": "dup_official_number_diff_base",
                "official_number": official,
                "policy_ids": pids,
            })
    return issues


def check_opinion_coverage(policies):
    """评论观点抽取覆盖率"""
    issues = []
    if not OPINIONS.exists():
        return issues
    opinion_files = list(OPINIONS.glob("*.md"))
    issues.append({
        "level": "info",
        "category": "opinion_coverage",
        "policies_with_opinions": len(opinion_files),
        "policies_total": len(policies),
        "ratio": round(len(opinion_files) / max(1, len(policies)), 2),
    })
    return issues


# -------- driver --------

def render_report(mode, all_issues):
    today = date.today().isoformat()
    by_cat = defaultdict(list)
    counts = {"error": 0, "warning": 0, "info": 0}
    for i in all_issues:
        by_cat[i["category"]].append(i)
        counts[i.get("level", "info")] += 1

    lines = []
    lines.append("---")
    lines.append(f"title: L2 lint · {mode} · {today}")
    lines.append(f"mode: {mode}")
    lines.append(f"date: {today}")
    lines.append(f"errors: {counts['error']}")
    lines.append(f"warnings: {counts['warning']}")
    lines.append(f"infos: {counts['info']}")
    lines.append("---")
    lines.append("")
    lines.append(f"# L2 lint · {mode} · {today}")
    lines.append("")
    lines.append(f"- ❌ errors: **{counts['error']}**")
    lines.append(f"- ⚠️ warnings: **{counts['warning']}**")
    lines.append(f"- ℹ️ infos: **{counts['info']}**")
    lines.append("")

    for cat in sorted(by_cat.keys()):
        items = by_cat[cat]
        lines.append(f"## {cat} ({len(items)})")
        lines.append("")
        for i in items[:20]:
            lvl = i.get("level", "info")
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(lvl, "·")
            detail = {k: v for k, v in i.items() if k not in ("level", "category")}
            lines.append(f"- {icon} {json.dumps(detail, ensure_ascii=False)}")
        if len(items) > 20:
            lines.append(f"- ... 还有 {len(items)-20} 条")
        lines.append("")
    return "\n".join(lines), counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["daily", "weekly"], help="lint 粒度")
    args = parser.parse_args()

    print(f"Running {args.mode} lint...")
    print("Loading data...")
    policies = load_policies()
    relations = load_relations()
    registry = load_registry()
    print(f"  {len(policies)} policies, {len(relations)} relations, {len(registry)} canonical entities")

    all_issues = []
    print("Checking frontmatter...")
    all_issues += check_policy_frontmatter(policies)
    print("Checking id uniqueness...")
    all_issues += check_id_uniqueness(policies)
    print("Checking relations validity...")
    all_issues += check_relations_valid(policies, relations)
    print("Checking region code consistency...")
    all_issues += check_region_code_consistency(policies)
    print("Checking entity extraction coverage...")
    all_issues += check_entity_extraction_coverage(policies)
    # diff coverage 检查已 deprecated(2026-05-07,SKILL §8e)
    print("Checking low-quality capture (body_len < 3KB)...")
    all_issues += check_low_quality_capture(policies)

    if args.mode == "weekly":
        print("[weekly] Checking orphan canonicals...")
        all_issues += check_orphan_canonicals(registry)
        print("[weekly] Checking extends direction...")
        all_issues += check_extends_direction(relations, policies)
        print("[weekly] Checking dup official numbers...")
        all_issues += check_dup_official_number(policies)
        print("[weekly] Checking opinion coverage...")
        all_issues += check_opinion_coverage(policies)

    report, counts = render_report(args.mode, all_issues)

    out_dir = LINTS / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date.today().isoformat()}.md"
    out_path.write_text(report, encoding="utf-8")

    print(f"\n=== {args.mode} lint summary ===")
    print(f"  errors:   {counts['error']}")
    print(f"  warnings: {counts['warning']}")
    print(f"  infos:    {counts['info']}")
    print(f"  report:   {out_path}")

    if counts["error"] > 0:
        sys.exit(2)
    elif counts["warning"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
