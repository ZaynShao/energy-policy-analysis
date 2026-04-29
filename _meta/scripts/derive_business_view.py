#!/usr/bin/env python3
"""
derive_business_view.py — Step 5C 业务侧派生(异步独立流程,严格分层版)

把 L1 raw 政策(0_raw/policies/{pid}.md)转成 3 个派生产物:
  1) _meta/business_view/{pid}.yaml    — 业务私有(scores/重要性/影响分析/行动建议)
  2) 1_extracted/policy_summaries.jsonl — 通用描述(summary/一句话/阅读价值)
  3) 1_extracted/relations/derives_from.jsonl — 国家级追溯关系(第 9 类 relation)

只读 raw,不修改 raw。一次 LLM 调用产出全字段,脚本侧 split 写 3 处。

用法:
  python3 derive_business_view.py --new           # 扫 0_raw/policies/ 找 business_view 缺失的,跑
  python3 derive_business_view.py --pid P_xxx     # 单条派生(指定 pid)
  python3 derive_business_view.py --rerun         # 对已有 business_view 也强制重跑(覆盖 LLM 字段)
  python3 derive_business_view.py --dry-run       # 不调 LLM 不写,只打印计划

环境变量:
  ANTHROPIC_API_KEY  — 必须

依赖:stdlib + requests + pyyaml
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
RAW = VAULT / "0_raw" / "policies"
BUSINESS_VIEW = VAULT / "_meta" / "business_view"
POLICY_SUMMARIES = VAULT / "1_extracted" / "policy_summaries.jsonl"
DERIVES_FROM = VAULT / "1_extracted" / "relations" / "derives_from.jsonl"

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = "claude-opus-4-5-20250929"
SCRIPT_TAG = "_meta/scripts/derive_business_view.py"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

PROMPT = """你是政策业务侧分析助手。输入是 L1 raw 政策(只读不改),输出业务侧派生 JSON。

服务对象:滴滴能源决策层,关注业务线为 加油 / 充电 / 电力(储能、虚拟电厂、需求响应、电力市场、绿电交易)+ 关注方向 乡村。

输出严格 JSON,无 markdown 代码块包裹,无解释:

{{
  "summary": "2-3 句客观摘要。描述政策范围/对象/截止日/数量目标。**不含**业务策略判断、跨政策对比、公司业务关联。",
  "summary_one_liner": "≤25 字一句话精髓。提取最核心的政策标的物或目标(如 '新型储能1.3亿千瓦+绿电扩面+碳市场扩面')。",
  "reading_value": "≤25 字阅读价值描述,谁该读、为何读(如 '2026业务OKR必读锚点')。",
  "national_source": {{
    "is_national_level_originated": true,
    "source_title": "源头政策标题或文号(本政策为国家级则填本政策标题;省/市级落地则填上层国家级文件标题或文号)",
    "linkage_type": null,
    "evidence": "文中对源头的引用或描述片段,≤120 字"
  }},
  "scores": {{
    "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0
  }},
  "影响分析": {{
    "加油": "...",
    "充电": "...",
    "电力_储能_V2G_交易": "...",
    "乡村": "..."
  }},
  "行动建议": [
    "A 立即/B 研究/C 关注: 具体动作"
  ]
}}

字段说明:
- summary: 2-3 句客观,不含品牌名,不含业务策略
- summary_one_liner / reading_value: 都 ≤25 字,中性表述
- national_source:
  - 国家级文件本身:`is_national_level_originated=true`,`source_title`="本政策标题",`linkage_type=null`
  - 省/市级落地文件:`is_national_level_originated=false`,`source_title`=上层国家级文件标题或文号,`linkage_type` 必填(枚举 "直接落地" | "借鉴框架" | "主题对应")
  - linkage_type 含义:**直接落地**=逐条对应执行国家文件;**借鉴框架**=参考国家方向自定细则;**主题对应**=同向部署但无明确引用
  - evidence:文中能佐证追溯关系的原文片段
  - 完全无国家级关联(纯地方独立创新):`is_national_level_originated=false`,`source_title=null`,`linkage_type=null`
- scores: 整数 0-5
  - D1 业务关联度: 政策直接影响滴滴四大业务的程度
  - D2 直接影响度: 政策落地后对滴滴业务实操的改变程度
  - D3 发布主体层级: 国务院/两办/部委 ≥4,省级 3,市级 2,区级 1
  - D4 紧迫性: 截止日近/已生效 ≥4,远期目标 1-2
  - D5 实操性: 已有配套细则可立即执行 ≥4,纲领性需等细则 1-2
  - D6 机会窗口: 创造新市场机会 ≥4,纯合规约束 1-2
- 影响分析:**可选**字段,只在 D1≥3 时写。每段 1 句,客观描述影响,**不写品牌名**(滴滴/能链等),不写"首批可落地"等业务策略判断。"乡村"是关注方向不是业务线,如政策无乡村相关内容可填"未涉及"。D1<3 时输出 null。
- 行动建议:**可选**字段,只在 D1≥3 时写。每条以 "A 立即:" / "B 研究:" / "C 关注:" 开头,1-2 句具体动作,可含跨业务建议。D1<3 时输出 []。

输入政策(L1 raw):

```markdown
{policy_text}
```

只输出 JSON。"""


def call_claude(prompt: str, max_retries: int = 2) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 环境变量未设置")

    body = {
        "model": MODEL,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(API_URL, headers=headers, json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            text = data["content"][0]["text"].strip()
            text = re.sub(r"^```(?:json)?\s*\n?|\n?```$", "", text).strip()
            return json.loads(text)
        except (json.JSONDecodeError, requests.RequestException, KeyError) as e:
            last_err = e
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"    重试 {attempt + 1}/{max_retries} after {wait}s: {e}", file=sys.stderr)
                time.sleep(wait)
    raise RuntimeError(f"LLM 调用 {max_retries + 1} 次都失败: {last_err}")


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


def read_l1_policy(p: Path) -> tuple[str, dict]:
    text = p.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        raise ValueError(f"no frontmatter: {p.name}")
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2).strip()
    return body, fm


def build_pid_index() -> dict[str, str]:
    """构建 lookup: title / official_number → pid。
    用于 derives_from 的 source_title 解析。冲突时取第一个。"""
    idx: dict[str, str] = {}
    for p in RAW.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
            m = FM_RE.match(text)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
        except (yaml.YAMLError, OSError):
            continue
        pid = fm.get("id") or p.stem
        title = (fm.get("title") or "").strip()
        official = (fm.get("official_number") or "").strip()
        if title:
            idx.setdefault(title, pid)
        if official:
            idx.setdefault(official, pid)
    return idx


def resolve_pid(source_title: str, idx: dict[str, str]) -> str | None:
    """source_title 解析到 pid。先尝试精确,再宽松包含。失败返回 None。"""
    if not source_title or not idx:
        return None
    s = source_title.strip()
    if s in idx:
        return idx[s]
    # 宽松:keys 长度 >= 6 且互相包含(避免短词误匹配)
    for k, v in idx.items():
        if len(k) >= 6 and (k in s or s in k):
            return v
    return None


def upsert_jsonl(path: Path, key: str, row: dict):
    """读 jsonl → 删 key 等于 row[key] 的旧行 → append 新行 → 写回全文件。
    适合 263 行级别 per-pid 重写。"""
    rows: list[dict] = []
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


def merge_into_business_view(pid: str, derived: dict, rerun: bool):
    """业务私有 yaml,merge 不覆盖已有(rerun=True 时强覆盖 LLM 字段)。"""
    bv_path = BUSINESS_VIEW / f"{pid}.yaml"
    if bv_path.exists():
        existing = yaml.safe_load(bv_path.read_text(encoding="utf-8")) or {}
    else:
        existing = {"pid": pid}

    for k, v in derived.items():
        if not rerun and k in existing and existing[k] not in (None, "", [], {}):
            continue
        existing[k] = v

    BUSINESS_VIEW.mkdir(parents=True, exist_ok=True)
    bv_path.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def derive_one(p: Path, pid_index: dict[str, str], dry_run: bool = False) -> dict:
    body, fm = read_l1_policy(p)
    pid = fm.get("id") or p.stem

    truncated_body = body[:8000]
    prompt = PROMPT.format(policy_text=truncated_body)

    if dry_run:
        return {"pid": pid, "path": p.name, "skipped": "dry-run"}

    llm_out = call_claude(prompt)

    summary = llm_out.get("summary", "")
    summary_one_liner = llm_out.get("summary_one_liner", "")
    reading_value = llm_out.get("reading_value", "")
    national_source = llm_out.get("national_source") or {}
    scores = llm_out.get("scores") or {}
    impact = llm_out.get("影响分析") or None
    actions = llm_out.get("行动建议") or []

    importance = compute_importance(scores)
    action = compute_action(importance, scores.get("D6", 0))
    now_iso = datetime.now().isoformat(timespec="seconds")

    business_view = {
        "scores": scores,
        "重要性": importance,
        "行动分类": action,
        "价值标签": [],
        "影响分析": impact,
        "行动建议": actions,
        "extracted_at": datetime.now().strftime("%Y-%m-%d"),
        "extracted_by": SCRIPT_TAG,
        "extracted_model": MODEL,
    }
    if importance < 3:
        business_view["archive"] = "low_score"

    summary_row = {
        "policy_id": pid,
        "summary": summary,
        "summary_one_liner": summary_one_liner,
        "reading_value": reading_value,
        "extracted_at": now_iso,
        "extracted_by": SCRIPT_TAG,
        "extracted_model": MODEL,
    }

    derives_row = None
    if national_source and not national_source.get("is_national_level_originated"):
        source_title = (national_source.get("source_title") or "").strip()
        linkage_type = national_source.get("linkage_type")
        evidence = (national_source.get("evidence") or "")[:300]
        if source_title and linkage_type in ("直接落地", "借鉴框架", "主题对应"):
            target_pid = resolve_pid(source_title, pid_index)
            derives_row = {
                "from": pid,
                "to": target_pid,
                "to_title": source_title,
                "rel": "derives_from",
                "linkage_type": linkage_type,
                "evidence": evidence,
                "confidence": 0.85,
                "extracted_by": SCRIPT_TAG,
                "extracted_at": now_iso,
            }

    return {
        "pid": pid,
        "path": p.name,
        "business_view": business_view,
        "summary_row": summary_row,
        "derives_row": derives_row,
    }


def find_targets(args) -> list[Path]:
    all_l1 = sorted(RAW.glob("*.md"))
    if args.pid:
        for p in all_l1:
            _, fm = read_l1_policy(p)
            if (fm.get("id") or p.stem) == args.pid:
                return [p]
        print(f"[error] 找不到 pid={args.pid}", file=sys.stderr)
        sys.exit(1)
    if args.rerun or args.all:
        return all_l1
    out = []
    for p in all_l1:
        _, fm = read_l1_policy(p)
        pid = fm.get("id") or p.stem
        bv_path = BUSINESS_VIEW / f"{pid}.yaml"
        if not bv_path.exists():
            out.append(p)
            continue
        bv = yaml.safe_load(bv_path.read_text(encoding="utf-8")) or {}
        # 缺 scores 或 行动建议 视为待派生(行动建议是新字段,旧 yaml 没有)
        if not bv.get("scores") or "行动建议" not in bv:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--new", action="store_true", help="扫缺失派生的(默认)")
    g.add_argument("--all", action="store_true", help="对全部 L1 政策跑(merge 已有)")
    g.add_argument("--pid", help="单条派生,指定 pid (如 P_2024_NDRC_718)")
    ap.add_argument("--rerun", action="store_true", help="覆盖已有 LLM 字段(否则 merge 不覆盖)")
    ap.add_argument("--dry-run", action="store_true", help="不调 LLM 不写")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 篇(0 = 全跑)")
    args = ap.parse_args()

    targets = find_targets(args)
    if args.limit:
        targets = targets[: args.limit]
    print(f"待派生: {len(targets)} 篇" + (" (dry-run)" if args.dry_run else ""))

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("[fatal] ANTHROPIC_API_KEY 未设置", file=sys.stderr)
        sys.exit(1)

    pid_index = build_pid_index() if not args.dry_run else {}
    if pid_index:
        print(f"pid 索引: {len(pid_index)} 条 (title + official_number)")

    ok = err = derives_written = 0
    for i, p in enumerate(targets, 1):
        try:
            r = derive_one(p, pid_index=pid_index, dry_run=args.dry_run)
            if args.dry_run:
                print(f"  [{i}/{len(targets)}] [dry] {r['pid']:<32} {r['path'][:50]}")
                ok += 1
                continue
            merge_into_business_view(r["pid"], r["business_view"], rerun=args.rerun)
            upsert_jsonl(POLICY_SUMMARIES, "policy_id", r["summary_row"])
            if r["derives_row"]:
                upsert_jsonl(DERIVES_FROM, "from", r["derives_row"])
                derives_written += 1
            bv = r["business_view"]
            ds_to = r["derives_row"]["to"] if r["derives_row"] else None
            print(
                f"  [{i}/{len(targets)}] {r['pid']:<32} 重要性={bv['重要性']} 行动={bv['行动分类']} "
                f"derives→{ds_to or '-'}"
            )
            ok += 1
        except Exception as e:
            err += 1
            print(f"  [{i}/{len(targets)}] [ERROR] {p.name[:60]}: {e}", file=sys.stderr)

    print(f"\n✅ 完成: ok={ok} err={err} derives_from 写入={derives_written}")


if __name__ == "__main__":
    main()
