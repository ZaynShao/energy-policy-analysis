#!/usr/bin/env python3
"""
standardize_issuer.py
P0a — 给 0_raw/policies/*.md frontmatter 加 issuer_canonical: [org_id, ...] 字段
原 issuer 字段不动(可回滚)。

策略:
  1. 读 registry.yaml 所有 type=[org] 实体 → {alias_str: canonical_id}
     (canonical_name 也作为一条"alias")
  2. 扫 289 政策 frontmatter
  3. 对每个 issuer 字符串(可能含"、"/"," 联合发文):
     a. 拆联合发文 + 去括号注释("国家能源局(河北省发改委转载)" → "国家能源局")
     b. 对每个拆出的机构名:
        i.   完全匹配 alias / canonical_name → 命中 canonical_id
        ii.  alias/canonical_name 是机构名子串(且长度 ≥4)→ 命中(模糊匹配)
        iii. 含"国家发展" + ("改革委"|"和改革委员会") → 推 ndrc(常见 ndrc 子部门/司局/办公厅)
        iv.  含"国家能源局" → 推 nea(同上)
        v.   不命中 → 入 review_queue
  4. 写 issuer_canonical: [unique org_id list]
  5. 输出 summary + review_queue

用法:
  python3 standardize_issuer.py --dry-run    # 不改文件,看命中率
  python3 standardize_issuer.py              # 正式跑
"""

import re
import sys
import yaml
import argparse
from pathlib import Path
from collections import Counter, defaultdict

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES_DIR = VAULT / "0_raw/policies"
REGISTRY = VAULT / "1_extracted/entities/registry.yaml"
META = VAULT / "_meta"
SUMMARY_OUT = META / "issuer_standardize_summary.md"
REVIEW_OUT = META / "issuer_review_queue.yaml"

FM_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)
PAREN_RE = re.compile(r"[（(].*?[）)]")  # 去括号注释


def load_org_aliases():
    """{alias_or_canonical_name: org_id} 反查表"""
    table = {}
    docs = list(yaml.safe_load_all(REGISTRY.open(encoding="utf-8")))
    all_e = []
    for d in docs:
        if isinstance(d, list):
            all_e.extend(d)
        elif isinstance(d, dict):
            all_e.append(d)
    for e in all_e:
        if "org" not in (e.get("type") or []):
            continue
        oid = e["id"]
        names = [e.get("canonical_name", "")] + (e.get("aliases") or [])
        for n in names:
            n = (n or "").strip()
            if n:
                table.setdefault(n, oid)  # 优先级:第一个出现的
    return table


def split_joint_issuer(s):
    """拆联合发文 'A、B、C' → ['A', 'B', 'C']"""
    s = PAREN_RE.sub("", s).strip()  # 去括号注释
    parts = re.split(r"[、,，；;]+", s)
    return [p.strip() for p in parts if p.strip()]


# 省/直辖市识别表(用于动态 canonical id 生成)
PROVINCE_PREFIXES = {
    "北京": "beijing", "上海": "shanghai", "天津": "tianjin", "重庆": "chongqing",
    "河北": "hebei", "山西": "shanxi", "辽宁": "liaoning", "吉林": "jilin",
    "黑龙江": "heilongjiang", "江苏": "jiangsu", "浙江": "zhejiang",
    "安徽": "anhui", "福建": "fujian", "江西": "jiangxi", "山东": "shandong",
    "河南": "henan", "湖北": "hubei", "湖南": "hunan", "广东": "guangdong",
    "海南": "hainan", "四川": "sichuan", "贵州": "guizhou", "云南": "yunnan",
    "陕西": "shaanxi", "甘肃": "gansu", "青海": "qinghai", "广西": "guangxi",
    "宁夏": "ningxia", "新疆": "xinjiang", "西藏": "xizang", "内蒙古": "neimenggu",
    "深圳": "shenzhen", "苏州": "suzhou", "杭州": "hangzhou", "南京": "nanjing",
    "武汉": "wuhan", "成都": "chengdu", "唐山": "tangshan", "汕尾": "shanwei",
}

# 国家部委补丁(registry 没单独建 org 的高频未命中)
NATIONAL_FALLBACK = [
    (["公安部"], "mps"),
    (["国家税务总局", "税务总局"], "sat"),
    (["中共中央"], "cccp_central"),
    (["金融监管总局", "国家金融监督管理总局"], "nfra"),
    (["国务院国有资产监督管理委员会", "国资委", "国务院国资委"], "sasac"),
    (["央行", "中国人民银行"], "pboc"),
    (["住建部", "住房和城乡建设部"], "mohurd"),
    (["国家自然科学基金委员会"], "nsfc"),
    (["国家林业和草原局", "国家林草局"], "nfga"),
    (["国家节能中心"], "ncec"),
    (["全国人民代表大会", "人大"], "npc"),
    (["国务院新闻办", "国新办"], "scio"),
    (["商务部新闻办公室", "商务部办公厅"], "mofcom"),
    (["新华日报", "新华社"], "xinhua_media"),
]


def match_one(name, alias_table):
    """返回 (org_id, match_type) 或 (None, None)

    匹配优先级:
      i.   完全匹配 alias / canonical_name(registry 注册过的 org)
      ii.  子串匹配(alias 是 name 的子串,且 alias 长度 ≥4)
      iii. ndrc/nea 启发式(常见子部门/司局/办公厅)
      iv.  国家部委补丁(NATIONAL_FALLBACK)
      v.   省/市级机构动态 id 生成(如 drc_beijing, gov_chongqing, miit_shanghai)
           * 这些 id 当前不在 registry,future weekly lint 可批量回填

    动态 id 命名规则:
      <category>_<region>
      category: drc(发改委) / nea(能源局) / miit(经信委)
              / commerce(商务委/局) / gov(政府/办公厅) / mof(财政) / 其他保留
      region:  province pinyin from PROVINCE_PREFIXES
    """
    # i. 完全匹配
    if name in alias_table:
        return alias_table[name], "exact"

    # ii. 子串匹配
    candidates = []
    for alias, oid in alias_table.items():
        if len(alias) >= 4 and alias in name:
            candidates.append((alias, oid))
    if candidates:
        alias, oid = max(candidates, key=lambda x: len(x[0]))
        return oid, f"substr({alias})"

    # iii. ndrc 启发式
    if ("国家发展" in name) and ("改革委" in name or "和改革委员会" in name):
        return "ndrc", "heuristic_ndrc"

    # iv. nea 启发式(国家级)
    if "国家能源局" in name:
        return "nea", "heuristic_nea"

    # v. 国家部委补丁
    for keywords, oid in NATIONAL_FALLBACK:
        if any(kw in name for kw in keywords):
            return oid, f"national_fallback({oid})"

    # vi. 省/市级机构动态 id
    matched_region = None
    for prefix, pinyin in PROVINCE_PREFIXES.items():
        if name.startswith(prefix):
            matched_region = pinyin
            break
    if matched_region:
        # 判 category(按关键词)
        if "发展" in name and ("改革委" in name or "和改革委员会" in name) or "发改委" in name:
            return f"drc_{matched_region}", "regional_drc"
        if "能源局" in name:
            return f"nea_{matched_region}", "regional_nea"
        if "经济" in name and ("信息化" in name or "信息" in name) or "经信" in name:
            return f"miit_{matched_region}", "regional_miit"
        if "商务" in name and ("局" in name or "委" in name):
            return f"commerce_{matched_region}", "regional_commerce"
        if "财政" in name:
            return f"mof_{matched_region}", "regional_mof"
        if "工业和信息化厅" in name or "工信厅" in name or "工信局" in name:
            return f"miit_{matched_region}", "regional_miit"
        if "市场监督管理局" in name or "市场监管局" in name:
            return f"samr_{matched_region}", "regional_samr"
        if "城市管理委员会" in name or "城管委" in name:
            return f"cma_{matched_region}", "regional_cma"
        if "交通运输厅" in name or "交通厅" in name or "交通运输局" in name:
            return f"mot_{matched_region}", "regional_mot"
        if "生态环境局" in name or "生态环境厅" in name:
            return f"mee_{matched_region}", "regional_mee"
        # 政府/办公厅 / 兜底
        if "人民政府" in name or "办公厅" in name or "办公室" in name:
            return f"gov_{matched_region}", "regional_gov"
        # 其他省级机构,标记需 review
        return f"other_{matched_region}", "regional_other"

    # 单独"发改委"/"能源局"(不带"国家")
    if name == "发改委" or name == "国家发改委":
        return "ndrc", "heuristic_ndrc"
    if name == "能源局":
        return "nea", "heuristic_nea"

    return None, None


def parse_fm_block(text):
    """返回 (header, fm_yaml_str, footer, body) 或 None"""
    m = FM_RE.match(text)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), text[m.end():]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="不改文件,只打印 summary + review_queue")
    args = parser.parse_args()

    alias_table = load_org_aliases()
    print(f"[init] {len(alias_table)} alias names → {len(set(alias_table.values()))} canonical org ids")

    files_modified = 0
    issuer_unique = Counter()       # raw issuer string → 出现次数
    matched_by_type = Counter()     # match_type → 计数
    miss_counter = Counter()        # 未命中 issuer string → 次数
    files_with_miss = []            # (file_name, [miss strings])
    files_all_match = 0

    for f in sorted(POLICIES_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        parts = parse_fm_block(text)
        if not parts:
            continue
        header, fm_yaml_str, footer, body = parts
        try:
            fm = yaml.safe_load(fm_yaml_str) or {}
        except yaml.YAMLError:
            continue
        issuers = fm.get("issuer") or []
        if isinstance(issuers, str):
            issuers = [issuers]

        canonical_set = []  # 保插入顺序
        misses = []
        for issuer_str in issuers:
            issuer_str = (issuer_str or "").strip()
            if not issuer_str:
                continue
            issuer_unique[issuer_str] += 1
            for sub in split_joint_issuer(issuer_str):
                oid, mtype = match_one(sub, alias_table)
                if oid:
                    matched_by_type[mtype.split("(")[0]] += 1
                    if oid not in canonical_set:
                        canonical_set.append(oid)
                else:
                    miss_counter[sub] += 1
                    misses.append(sub)

        if misses:
            files_with_miss.append((f.name, misses))
        else:
            files_all_match += 1

        if not args.dry_run and canonical_set:
            # 写回 frontmatter,加 issuer_canonical
            fm["issuer_canonical"] = canonical_set
            new_yaml = yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip()
            new_text = header + new_yaml + footer + body
            f.write_text(new_text, encoding="utf-8")
            files_modified += 1

    total = len(list(POLICIES_DIR.glob("*.md")))
    hit_pct = files_all_match / total * 100 if total else 0

    # ===== summary =====
    summary_lines = [
        "# issuer 标准化跑通报告",
        "",
        f"- 政策总数:**{total}**",
        f"- 完全命中(无 miss):**{files_all_match}**({hit_pct:.1f}%)",
        f"- 含未命中机构的政策:**{len(files_with_miss)}**",
        f"- 文件改动:{'(dry-run, 0)' if args.dry_run else files_modified}",
        "",
        "## match_type 分布",
        ""
    ]
    for mt, n in matched_by_type.most_common():
        summary_lines.append(f"- {mt}: {n}")
    summary_lines.extend([
        "",
        f"## 未命中机构 Top 30(按出现频次)",
        "",
    ])
    for s, n in miss_counter.most_common(30):
        summary_lines.append(f"- {n:3d} × `{s}`")

    print("\n" + "\n".join(summary_lines))

    if not args.dry_run:
        SUMMARY_OUT.write_text("\n".join(summary_lines), encoding="utf-8")
        print(f"\n[out] summary → {SUMMARY_OUT}")
        # 写 review_queue
        review = {
            "instructions": "未命中的 issuer 子串,按频次降序。补到 registry.yaml 对应 org 实体的 aliases,然后重跑本脚本。",
            "miss_strings": [
                {"name": s, "count": n} for s, n in miss_counter.most_common()
            ],
            "files_with_miss_top_20": [
                {"file": fn, "misses": ms} for fn, ms in files_with_miss[:20]
            ],
        }
        REVIEW_OUT.write_text(
            yaml.safe_dump(review, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8"
        )
        print(f"[out] review_queue → {REVIEW_OUT}")


if __name__ == "__main__":
    main()
