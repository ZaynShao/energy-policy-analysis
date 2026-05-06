#!/usr/bin/env python3
"""
文号序列审计(本地无 API,可立刻跑)
扫描 vault 已收政策的发文文号,找出每个机构当年的文号缺号 → 形成补抓清单

例:
  vault 收了:
    苏发改能源发〔2025〕1198 号 (江苏省发改委 2025 年 第 1198 号)
  搜索结果显示江苏省发改委 2025 年发了 1300+ 号 → 补抓 1-1197 与 1199-1300 的能源/电力相关号

输入: 0_raw/policies/*.md 的 official_number frontmatter 字段
输出:
  - 文号矩阵: {发文机构: {年份: [已知号码列表]}}
  - 缺号清单: {发文机构: {年份: 缺号区间}}
"""
import os
import re
import yaml
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent


def parse_frontmatter(content):
    """提取 markdown 文件 frontmatter"""
    if not content.startswith("---\n"):
        return {}
    try:
        end = content.index("\n---\n", 4)
        fm = content[4:end]
        return yaml.safe_load(fm) or {}
    except Exception:
        return {}


def parse_official_number(s):
    """
    解析文号:
      "苏发改能源发〔2025〕1198号" → ("苏发改能源发", 2025, 1198)
      "国办发〔2020〕39号"          → ("国办发", 2020, 39)
      "发改综合〔2023〕545号"        → ("发改综合", 2023, 545)
      "发改能源规〔2022〕53号"       → ("发改能源规", 2022, 53)
    """
    if not s or not isinstance(s, str):
        return None
    m = re.search(r"([一-龥A-Z]+?)〔(\d{4})〕\s*(\d+)\s*号", s)
    if m:
        return (m.group(1), int(m.group(2)), int(m.group(3)))
    return None


def main():
    raw_dir = ROOT / "0_raw" / "policies"
    by_issuer_year = defaultdict(lambda: defaultdict(list))  # issuer -> year -> [seq]
    parsed = 0
    skipped = 0

    for f in sorted(os.listdir(raw_dir)):
        if not f.endswith(".md"):
            continue
        try:
            content = (raw_dir / f).read_text()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        # frontmatter 字段名兼容: official_number / official / 文号
        on = fm.get("official_number") or fm.get("official") or fm.get("文号")
        # body 中文号(若 frontmatter 没有,从标题正则)
        if not on:
            m = re.search(r"〔\d{4}〕\d+号", content[:500])
            if m:
                on = m.group(0)
        triplet = parse_official_number(on) if on else None
        if triplet:
            issuer, year, seq = triplet
            by_issuer_year[issuer][year].append(seq)
            parsed += 1
        else:
            skipped += 1

    # 生成缺号清单
    gaps = {}
    summary_lines = []
    summary_lines.append(f"# 文号序列审计 ({parsed} 篇有文号 / {skipped} 篇无文号)\n")
    summary_lines.append("## 各发文机构 × 年 文号区间\n")
    summary_lines.append("| 发文机构 | 年份 | 收录数 | 最小号 | 最大号 | 缺号数 | 缺号示例 |")
    summary_lines.append("|---|---|---:|---:|---:|---:|---|")

    for issuer, by_year in sorted(by_issuer_year.items()):
        for year, seqs in sorted(by_year.items()):
            seqs = sorted(set(seqs))
            n = len(seqs)
            mn, mx = seqs[0], seqs[-1]
            full_range = set(range(mn, mx + 1))
            missing = sorted(full_range - set(seqs))
            sample = ",".join(map(str, missing[:5])) + ("..." if len(missing) > 5 else "")
            summary_lines.append(
                f"| {issuer} | {year} | {n} | {mn} | {mx} | {len(missing)} | {sample} |"
            )
            if missing:
                gaps[f"{issuer}_{year}"] = {"issuer": issuer, "year": year,
                                              "known_min": mn, "known_max": mx,
                                              "missing": missing}

    out_md = AUDIT_DIR / "official_number_audit.md"
    out_md.write_text("\n".join(summary_lines))

    out_json = AUDIT_DIR / "official_number_gaps.json"
    out_json.write_text(json.dumps(gaps, ensure_ascii=False, indent=2))

    print(f"=== 文号序列审计完成 ===")
    print(f"已收文号: {parsed} 篇 / 无文号: {skipped} 篇")
    print(f"机构 × 年组合: {sum(len(by_year) for by_year in by_issuer_year.values())}")
    print(f"摘要 -> {out_md}")
    print(f"缺号清单 -> {out_json}")
    print(f"\n注: 当前 vault 单机构单年命中 1-3 篇是常态,'缺号'更多反映")
    print(f"我们没收 vs 真没发,需要后续 Tavily site:filter 验证")


if __name__ == "__main__":
    main()
