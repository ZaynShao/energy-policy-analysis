#!/usr/bin/env python3
"""
本地覆盖度 baseline (无 API 调用,纯读 vault)
输出: 13 主题 × 31 省 × 重点地市 当前覆盖度矩阵

数据源:
  - 5 现有主题: 2_crystallized/themes/<theme>/_input.json
  - 4 新增主题: 0_raw/policies/ 全文 grep aliases (用 entities 匹配)
  - 4 其他现有主题(碳市场/绿电/加油站/设备更新): 同上,如有 _input.json 用之
  - 31 省 + ~80 重点地市清单: target_cities.yaml
"""
import json
import os
import re
import yaml
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = Path(__file__).resolve().parent

PROVINCE_NAME_TO_CODE = {
    "北京市": "110000", "天津市": "120000", "河北省": "130000", "山西省": "140000",
    "内蒙古自治区": "150000", "辽宁省": "210000", "吉林省": "220000", "黑龙江省": "230000",
    "上海市": "310000", "江苏省": "320000", "浙江省": "330000", "安徽省": "340000",
    "福建省": "350000", "江西省": "360000", "山东省": "370000",
    "河南省": "410000", "湖北省": "420000", "湖南省": "430000",
    "广东省": "440000", "广西壮族自治区": "450000", "海南省": "460000",
    "重庆市": "500000", "四川省": "510000", "贵州省": "520000", "云南省": "530000",
    "西藏自治区": "540000",
    "陕西省": "610000", "甘肃省": "620000", "青海省": "630000",
    "宁夏回族自治区": "640000", "新疆维吾尔自治区": "650000",
}
PROVINCE_KEYWORDS = {  # 用于 raw 文件名 / body grep
    "北京": "110000", "天津": "120000", "河北": "130000", "山西": "140000",
    "内蒙古": "150000", "辽宁": "210000", "吉林": "220000", "黑龙江": "230000",
    "上海": "310000", "江苏": "320000", "浙江": "330000", "安徽": "340000",
    "福建": "350000", "江西": "360000", "山东": "370000",
    "河南": "410000", "湖北": "420000", "湖南": "430000",
    "广东": "440000", "广西": "450000", "海南": "460000",
    "重庆": "500000", "四川": "510000", "贵州": "520000", "云南": "530000",
    "西藏": "540000",
    "陕西": "610000", "甘肃": "620000", "青海": "630000",
    "宁夏": "640000", "新疆": "650000",
}


def load_themes():
    return yaml.safe_load(open(AUDIT_DIR / "themes_13.yaml"))["themes"]


def load_target_cities():
    return yaml.safe_load(open(AUDIT_DIR / "target_cities.yaml"))


def existing_theme_input(dir_name):
    p = ROOT / "2_crystallized" / "themes" / dir_name / "_input.json"
    if p.exists():
        return json.load(open(p))
    return None


def all_raw_policies():
    """枚举 0_raw/policies/ 下全部 raw 文件,返回 [{filename, content}]"""
    out = []
    for f in sorted(os.listdir(ROOT / "0_raw" / "policies")):
        if not f.endswith(".md"):
            continue
        path = ROOT / "0_raw" / "policies" / f
        try:
            content = path.read_text()
        except Exception:
            continue
        out.append({"filename": f, "path": str(path), "content": content})
    return out


def detect_province_from_filename(fn):
    for kw, code in PROVINCE_KEYWORDS.items():
        if kw in fn:
            return code, kw
    return None, None


def detect_theme_match(content, aliases):
    """返回命中的 alias 数(简单 grep)"""
    n = 0
    for a in aliases:
        if a in content:
            n += 1
    return n


def main():
    themes = load_themes()
    tc = load_target_cities()
    provinces = tc["provinces"]

    raw = all_raw_policies()
    print(f"读取 raw 政策: {len(raw)} 篇")

    # 主题命中矩阵: theme_id × province_code = count
    matrix = defaultdict(lambda: Counter())
    theme_hits = defaultdict(int)  # 主题级总数
    raw_meta = []

    for rec in raw:
        prov_code, prov_kw = detect_province_from_filename(rec["filename"])
        # 国家级判定
        if not prov_code:
            for natkw in ["国务院", "国家发展", "国家发改委", "发改委", "国家能源局",
                          "能源局", "工信部", "工业和信息化部", "商务部", "财政部",
                          "生态环境部", "住建部", "住房和城乡建设部", "交通运输部",
                          "市场监管总局"]:
                if natkw in rec["filename"]:
                    prov_code = "000000"
                    prov_kw = "国家级"
                    break

        for th in themes:
            n = detect_theme_match(rec["content"][:5000] + rec["filename"], th["aliases"])
            if n >= 1:
                if prov_code:
                    matrix[th["id"]][prov_code] += 1
                theme_hits[th["id"]] += 1

        raw_meta.append({"filename": rec["filename"], "province": prov_code, "kw": prov_kw})

    # 输出 1: 主题 × 省 矩阵
    rows = ["theme_id\tzh\t业务线\tP\t国家级"]
    prov_codes_sorted = sorted({p["code"] for p in provinces})
    rows[0] += "\t" + "\t".join(p["name"] for p in provinces)
    for th in themes:
        tier = "P0"
        # 从 themes_13 取 priority(简化,未读)
        zh = th["zh"]
        bl = th["business_line"]
        nat = matrix[th["id"]].get("000000", 0)
        cells = [str(matrix[th["id"]].get(p["code"], 0)) for p in provinces]
        rows.append(f"{th['id']}\t{zh}\t{bl}\t{tier}\t{nat}\t" + "\t".join(cells))

    out_tsv = AUDIT_DIR / "coverage_matrix.tsv"
    out_tsv.write_text("\n".join(rows))
    print(f"\nTSV 矩阵 -> {out_tsv}")

    # 输出 2: 摘要
    summary_lines = []
    summary_lines.append(f"# 本地覆盖度 baseline ({len(raw)} raw policies)\n")
    summary_lines.append("## 13 主题命中数(基于 raw body+title alias grep)\n")
    summary_lines.append("| 主题 | 业务线 | 命中 raw 数 | 国家级 | 省级总数 | 省份覆盖 |")
    summary_lines.append("|---|---|---:|---:|---:|---:|")
    for th in themes:
        nat = matrix[th["id"]].get("000000", 0)
        prov_total = sum(c for k, c in matrix[th["id"]].items() if k != "000000")
        prov_distinct = sum(1 for k, c in matrix[th["id"]].items() if k != "000000" and c > 0)
        summary_lines.append(
            f"| {th['zh']} | {th['business_line']} | {theme_hits[th['id']]} | {nat} | {prov_total} | {prov_distinct}/31 |"
        )

    summary_lines.append("\n## 31 省份政策总分布(按文件名 keyword 推断)\n")
    summary_lines.append("| 省份 | code | raw 政策数 |")
    summary_lines.append("|---|---|---:|")
    prov_total = Counter()
    for r in raw_meta:
        if r["province"]:
            prov_total[r["province"]] += 1
    for p in provinces:
        summary_lines.append(f"| {p['name']} | {p['code']} | {prov_total.get(p['code'], 0)} |")
    summary_lines.append(f"| 国家级 | 000000 | {prov_total.get('000000', 0)} |")

    summary_lines.append("\n## 主题×省份覆盖矩阵稀疏度\n")
    total_cells = len(themes) * 31
    nonzero = sum(1 for th in themes for p in provinces if matrix[th["id"]].get(p["code"], 0) > 0)
    summary_lines.append(f"- 总 cell 数: {total_cells}")
    summary_lines.append(f"- 非零 cell: {nonzero} ({nonzero/total_cells*100:.1f}%)")
    summary_lines.append(f"- **零 cell(漏抓候选)**: {total_cells - nonzero}")

    summary_lines.append("\n## P0 主题(滴滴电力业务核心)的零省份清单\n")
    p0_themes = ["vpp_theme", "energy_storage_theme", "power_market", "v2g",
                 "aggregator_access", "distribution_grid_opening"]
    for th_id in p0_themes:
        th = next(x for x in themes if x["id"] == th_id)
        zero_provs = [p["name"] for p in provinces if matrix[th_id].get(p["code"], 0) == 0]
        summary_lines.append(f"- **{th['zh']}** 零省: {', '.join(zero_provs)}")

    out_md = AUDIT_DIR / "coverage_baseline.md"
    out_md.write_text("\n".join(summary_lines))
    print(f"摘要 -> {out_md}")

    # 输出 3: matrix.json
    matrix_json = {th["id"]: dict(matrix[th["id"]]) for th in themes}
    (AUDIT_DIR / "coverage_matrix.json").write_text(json.dumps(matrix_json, ensure_ascii=False, indent=2))
    print(f"matrix.json -> {AUDIT_DIR / 'coverage_matrix.json'}")


if __name__ == "__main__":
    main()
