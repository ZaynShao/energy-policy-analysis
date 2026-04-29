#!/usr/bin/env python3
"""
derive_business_view.py — Step 5C 业务侧派生(异步独立流程)

把 L1 raw 政策(0_raw/policies/{pid}.md)转成业务侧派生(_meta/business_view/{pid}.yaml)。
只读 raw,不修改 raw。

调用 Claude Opus 4.7 抽取:summary / business_tags / scores(D1-D6) / 影响分析。
脚本侧确定性计算:重要性(综合分) / archive 标记。

用法:
  python3 derive_business_view.py --new           # 扫 0_raw/policies/ 找 business_view 缺失的,跑
  python3 derive_business_view.py --pid P_xxx     # 单条派生(指定 pid)
  python3 derive_business_view.py --rerun         # 对已有 business_view 也强制重跑(覆盖 LLM 字段,保留 sanitized_* 元数据)
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

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = "claude-opus-4-5-20250929"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

PROMPT = """你是政策业务侧分析助手。输入是 L1 raw 政策(只读不改),输出业务侧派生 JSON。

服务对象:滴滴能源决策层,关注业务线为 加油 / 充电 / 电力(储能、虚拟电厂、需求响应、电力市场、绿电)。

输出严格 JSON,无 markdown 代码块包裹,无解释:

{{
  "summary": "2-3 句客观摘要。描述政策范围/对象/截止日/数量目标。**不含**业务策略判断、跨政策对比、公司业务关联。",
  "business_tags": ["..."],
  "scores": {{
    "D1": 0,
    "D2": 0,
    "D3": 0,
    "D4": 0,
    "D5": 0,
    "D6": 0
  }},
  "影响分析": {{
    "加油业务": "...",
    "充电业务": "...",
    "电力业务": "..."
  }}
}}

字段说明:
- business_tags: 多选,枚举值仅限 [V2G, 储能, 充电, 加油, 综合能源, 电力市场, 碳排放, 设备更新, 新能源汽车, 氢能, 节能降碳, 虚拟电厂, 需求响应, 绿电交易]。空数组 [] 表示与上述业务全无关。
- scores: 整数 0-5
  - D1 业务关联度: 政策直接影响滴滴四大业务的程度
  - D2 直接影响度: 政策落地后对滴滴业务实操的改变程度
  - D3 发布主体层级: 国务院/两办/部委 ≥4,省级 3,市级 2,区级 1
  - D4 紧迫性: 截止日近/已生效 ≥4,远期目标 1-2
  - D5 实操性: 已有配套细则可立即执行 ≥4,纲领性需等细则 1-2
  - D6 机会窗口: 创造新市场机会 ≥4,纯合规约束 1-2
- 影响分析:**可选**字段,只在 D1≥3 时写。每段 1 句,客观描述影响,不写"滴滴""能链"等品牌名,不写"首批可落地"等业务策略判断。D1<3 时输出 null。

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


def derive_one(p: Path, dry_run: bool = False) -> dict:
    body, fm = read_l1_policy(p)
    pid = fm.get("id") or p.stem

    truncated_body = body[:8000]
    prompt = PROMPT.format(policy_text=truncated_body)

    if dry_run:
        return {"pid": pid, "path": p.name, "skipped": "dry-run"}

    llm_out = call_claude(prompt)

    summary = llm_out.get("summary", "")
    business_tags = llm_out.get("business_tags") or []
    scores = llm_out.get("scores") or {}
    impact = llm_out.get("影响分析") or None

    importance = compute_importance(scores)
    action = compute_action(importance, scores.get("D6", 0))

    derived = {
        "summary": summary,
        "business_tags": business_tags,
        "scores": scores,
        "重要性": importance,
        "行动分类": action,
        "价值标签": [],
        "影响分析": impact,
        "extracted_at": datetime.now().strftime("%Y-%m-%d"),
        "extracted_by": "_meta/scripts/derive_business_view.py",
        "extracted_model": MODEL,
    }
    if importance < 3:
        derived["archive"] = "low_score"
    return {"pid": pid, "path": p.name, "derived": derived}


def merge_into_yaml(pid: str, derived: dict, rerun: bool):
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
        if not bv.get("scores") or not bv.get("summary"):
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

    ok = err = 0
    for i, p in enumerate(targets, 1):
        try:
            r = derive_one(p, dry_run=args.dry_run)
            if args.dry_run:
                print(f"  [{i}/{len(targets)}] [dry] {r['pid']:<32} {r['path'][:50]}")
                ok += 1
                continue
            merge_into_yaml(r["pid"], r["derived"], rerun=args.rerun)
            d = r["derived"]
            print(
                f"  [{i}/{len(targets)}] {r['pid']:<32} 重要性={d['重要性']} 行动={d['行动分类']} "
                f"tags={','.join(d['business_tags'][:3])}{'...' if len(d['business_tags'])>3 else ''}"
            )
            ok += 1
        except Exception as e:
            err += 1
            print(f"  [{i}/{len(targets)}] [ERROR] {p.name[:60]}: {e}", file=sys.stderr)

    print(f"\n✅ 完成: ok={ok} err={err}")


if __name__ == "__main__":
    main()
