#!/usr/bin/env python3
"""
Stage F: 把 staging 里的 markdown 转成 SOP-compliant raw 政策

输入: 0_raw/policies_staging_2026-05-06/<slug>.md (fetcher 写的)
输出:
  - 0_raw/policies/【title】-issuer-hash8.md (SOP 格式)
  - dedup 报告
  - new_pids.txt (供 trigger A prepare 用)

字段抽取 (deterministic):
  - id: P_YYYY_<region_code>_<8hash>
  - title: 从原始 fetcher frontmatter
  - official_number: 从 title/body 头部正则
  - issuer: 从 url 域名 → 渠道目录映射
  - date: 从 url path / body 头部正则 (YYYY-MM-DD)
  - region: 从 url 域名 推断 (gov.cn 子域 → 行政区划)
  - provenance: {url, fetched_at, fetched_method, content_type}
  - type: policy
"""
import argparse
import json
import os
import re
import sys
import yaml
import hashlib
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "0_raw" / "policies_staging_2026-05-06"
TARGET = ROOT / "0_raw" / "policies"


# 域名 → (region_code, region_name, issuer_guess)
DOMAIN_REGION = {
    # 中央
    "www.gov.cn":      ("000000", "全国", "国务院"),
    "www.ndrc.gov.cn": ("000000", "全国", "国家发展和改革委员会"),
    "www.nea.gov.cn":  ("000000", "全国", "国家能源局"),
    "www.miit.gov.cn": ("000000", "全国", "工业和信息化部"),
    "www.mofcom.gov.cn": ("000000", "全国", "商务部"),
    "www.mof.gov.cn":  ("000000", "全国", "财政部"),
    "www.mohurd.gov.cn": ("000000", "全国", "住房和城乡建设部"),
    "www.mee.gov.cn":  ("000000", "全国", "生态环境部"),
    "zfxxgk.nea.gov.cn": ("000000", "全国", "国家能源局"),
    # 省级 (不全, 只覆盖关键的)
    "fgw.beijing.gov.cn": ("110000", "北京市", "北京市发展和改革委员会"),
    "www.beijing.gov.cn": ("110000", "北京市", "北京市人民政府"),
    "fzgg.tj.gov.cn":   ("120000", "天津市", "天津市发展和改革委员会"),
    "www.tj.gov.cn":    ("120000", "天津市", "天津市人民政府"),
    "hbdrc.hebei.gov.cn": ("130000", "河北省", "河北省发展和改革委员会"),
    "info.hebei.gov.cn": ("130000", "河北省", "河北省人民政府"),
    "fgw.shanxi.gov.cn": ("140000", "山西省", "山西省发展和改革委员会"),
    "fgw.nmg.gov.cn":   ("150000", "内蒙古自治区", "内蒙古自治区发展和改革委员会"),
    "fgw.ln.gov.cn":    ("210000", "辽宁省", "辽宁省发展和改革委员会"),
    "fzggw.jl.gov.cn":  ("220000", "吉林省", "吉林省发展和改革委员会"),
    "drc.hlj.gov.cn":   ("230000", "黑龙江省", "黑龙江省发展和改革委员会"),
    "fgw.sh.gov.cn":    ("310000", "上海市", "上海市发展和改革委员会"),
    "www.shanghai.gov.cn": ("310000", "上海市", "上海市人民政府"),
    "fzggw.jiangsu.gov.cn": ("320000", "江苏省", "江苏省发展和改革委员会"),
    "www.jiangsu.gov.cn": ("320000", "江苏省", "江苏省人民政府"),
    "nyj.jiangsu.gov.cn": ("320000", "江苏省", "江苏省能源局"),
    "fzggw.zj.gov.cn":  ("330000", "浙江省", "浙江省发展和改革委员会"),
    "www.zj.gov.cn":    ("330000", "浙江省", "浙江省人民政府"),
    "zjnyj.zj.gov.cn":  ("330000", "浙江省", "浙江省能源局"),
    "fzggw.ah.gov.cn":  ("340000", "安徽省", "安徽省发展和改革委员会"),
    "www.ah.gov.cn":    ("340000", "安徽省", "安徽省人民政府"),
    "fgw.fujian.gov.cn": ("350000", "福建省", "福建省发展和改革委员会"),
    "www.fujian.gov.cn": ("350000", "福建省", "福建省人民政府"),
    "drc.jiangxi.gov.cn": ("360000", "江西省", "江西省发展和改革委员会"),
    "fgw.shandong.gov.cn": ("370000", "山东省", "山东省发展和改革委员会"),
    "nyj.shandong.gov.cn": ("370000", "山东省", "山东省能源局"),
    "www.shandong.gov.cn": ("370000", "山东省", "山东省人民政府"),
    "fgw.henan.gov.cn":  ("410000", "河南省", "河南省发展和改革委员会"),
    "www.henan.gov.cn":  ("410000", "河南省", "河南省人民政府"),
    "fgw.hubei.gov.cn":  ("420000", "湖北省", "湖北省发展和改革委员会"),
    "www.hubei.gov.cn":  ("420000", "湖北省", "湖北省人民政府"),
    "fgw.hunan.gov.cn":  ("430000", "湖南省", "湖南省发展和改革委员会"),
    "www.hunan.gov.cn":  ("430000", "湖南省", "湖南省人民政府"),
    "drc.gd.gov.cn":     ("440000", "广东省", "广东省发展和改革委员会"),
    "www.gd.gov.cn":     ("440000", "广东省", "广东省人民政府"),
    "fgw.gxzf.gov.cn":   ("450000", "广西壮族自治区", "广西壮族自治区发展和改革委员会"),
    "plan.hainan.gov.cn": ("460000", "海南省", "海南省发展和改革委员会"),
    "www.hainan.gov.cn": ("460000", "海南省", "海南省人民政府"),
    "fzggw.cq.gov.cn":   ("500000", "重庆市", "重庆市发展和改革委员会"),
    "www.cq.gov.cn":     ("500000", "重庆市", "重庆市人民政府"),
    "fgw.sc.gov.cn":     ("510000", "四川省", "四川省发展和改革委员会"),
    "www.sc.gov.cn":     ("510000", "四川省", "四川省人民政府"),
    "fgw.guizhou.gov.cn": ("520000", "贵州省", "贵州省发展和改革委员会"),
    "yndrc.yn.gov.cn":   ("530000", "云南省", "云南省发展和改革委员会"),
    "sndrc.shaanxi.gov.cn": ("610000", "陕西省", "陕西省发展和改革委员会"),
    "fzgg.gansu.gov.cn": ("620000", "甘肃省", "甘肃省发展和改革委员会"),
    "fgw.qinghai.gov.cn": ("630000", "青海省", "青海省发展和改革委员会"),
    "fzggw.nx.gov.cn":   ("640000", "宁夏回族自治区", "宁夏回族自治区发展和改革委员会"),
}


def detect_region_issuer(url):
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return ("000000", "未知", "未知机构")
    if host in DOMAIN_REGION:
        return DOMAIN_REGION[host]
    # gov.cn 子域 → 找 longest match
    for d in sorted(DOMAIN_REGION, key=len, reverse=True):
        if host.endswith("." + d) or host == d:
            return DOMAIN_REGION[d]
    # 通配判断: *.gov.cn → 至少识别为政府,issuer 用 host
    if host.endswith(".gov.cn"):
        # 提取省/市关键词
        parts = host.split(".")
        if len(parts) >= 3 and parts[-2] == "gov" and parts[-1] == "cn":
            tier = parts[-3]
            return ("000000", "未知", f"政府门户.{host}")
    return ("000000", "未知", "未知机构")


def extract_official_number(text):
    if not text:
        return ""
    m = re.search(r"[一-龥A-Z]{2,8}?〔(\d{4})〕\s*(\d{1,5})\s*号", text)
    return re.sub(r"\s+", "", m.group(0)) if m else ""


def extract_date(url, body):
    # 1) URL path 中的 YYYY-MM-DD 或 YYYY/MM 或 YYYYMM
    if url:
        for pat in [r"/(\d{4})-(\d{1,2})-(\d{1,2})/", r"/(\d{4})/(\d{2})-(\d{2})/",
                    r"/(\d{4})/(\d{1,2})/", r"_(\d{4})(\d{2})(\d{2})\.", r"/(\d{4})(\d{2})(\d{2})/"]:
            m = re.search(pat, url)
            if m:
                try:
                    g = m.groups()
                    if len(g) == 3:
                        y, mo, d = int(g[0]), int(g[1]), int(g[2])
                        if 2018 <= y <= 2027 and 1 <= mo <= 12 and 1 <= d <= 31:
                            return f"{y:04d}-{mo:02d}-{d:02d}"
                    elif len(g) == 2:
                        return f"{int(g[0]):04d}-{int(g[1]):02d}-01"
                except Exception:
                    pass
    # 2) body 头部 1000 字找
    if body:
        head = body[:1500]
        for pat in [r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                    r"(\d{4})-(\d{1,2})-(\d{1,2})", r"发布时间[::\s]+(\d{4})-(\d{1,2})-(\d{1,2})"]:
            m = re.search(pat, head)
            if m:
                try:
                    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    if 2018 <= y <= 2027 and 1 <= mo <= 12 and 1 <= d <= 31:
                        return f"{y:04d}-{mo:02d}-{d:02d}"
                except Exception:
                    pass
    return ""


def gen_pid(date, region_code, slug):
    """P_YYYY_<region_short>_<hash8>"""
    year = (date or "1900-01-01")[:4]
    # region 短码: 前 2 位数字 + 文字简称
    region_short_map = {
        "000000": "GO", "110000": "BJ", "120000": "TJ", "130000": "HE",
        "140000": "SX", "150000": "NM", "210000": "LN", "220000": "JL",
        "230000": "HL", "310000": "SH", "320000": "JS", "330000": "ZJ",
        "340000": "AH", "350000": "FJ", "360000": "JX", "370000": "SD",
        "410000": "HA", "420000": "HB", "430000": "HN", "440000": "GD",
        "450000": "GX", "460000": "HI", "500000": "CQ", "510000": "SC",
        "520000": "GZ", "530000": "YN", "540000": "XZ", "610000": "SN",
        "620000": "GS", "630000": "QH", "640000": "NX", "650000": "XJ",
    }
    rc = region_short_map.get(region_code, "XX")
    return f"P_{year}_{rc}_{slug[:8]}"


def slugify_filename(title, issuer, official_number, slug_hash):
    """SOP 命名: 【<title>(<official>)】-<issuer>-<8hash>.md"""
    title_clean = re.sub(r"[\\/:*?\"<>|]", "", title)[:80]
    issuer_clean = re.sub(r"[\\/:*?\"<>|]", "", issuer)[:30]
    if official_number:
        return f"【{title_clean}({official_number})】-{issuer_clean}-{slug_hash}.md"
    return f"【{title_clean}】-{issuer_clean}-{slug_hash}.md"


def main():
    global STAGING
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default=None,
                    help="staging dir override (default: 0_raw/policies_staging_2026-05-06)")
    args = ap.parse_args()
    if args.staging:
        STAGING = Path(args.staging).resolve()
        print(f"STAGING override: {STAGING}")
    if not STAGING.exists():
        print(f"ERROR: staging dir not found: {STAGING}")
        sys.exit(1)

    new_files = []
    skipped = 0
    skipped_reasons = []

    # 加载现有 vault 的 url 集合避免重抓重入
    known_urls = set()
    known_titles = set()
    known_officials = set()
    for f in os.listdir(TARGET):
        if not f.endswith(".md"):
            continue
        try:
            content = (TARGET / f).read_text()
            if content.startswith("---\n"):
                end = content.index("\n---\n", 4)
                fm = yaml.safe_load(content[4:end]) or {}
                prov = fm.get("provenance", {}) or {}
                u = prov.get("url") or prov.get("source_url")
                if u: known_urls.add(u.strip())
                t = fm.get("title", "")
                if t:
                    tnorm = re.sub(r"[\s，。、（）()《》\"\']", "", t)
                    known_titles.add(tnorm)
                on = fm.get("official_number") or fm.get("official")
                if on: known_officials.add(re.sub(r"\s+", "", str(on)))
        except Exception:
            pass

    print(f"vault known: {len(known_urls)} urls, {len(known_titles)} titles, {len(known_officials)} officials")

    for sf in sorted(os.listdir(STAGING)):
        if not sf.endswith(".md"):
            continue
        path = STAGING / sf
        try:
            content = path.read_text()
        except Exception as e:
            skipped += 1
            skipped_reasons.append(f"read fail: {sf}: {e}")
            continue
        # 解析 fetcher frontmatter
        if not content.startswith("---\n"):
            skipped += 1
            skipped_reasons.append(f"no frontmatter: {sf}")
            continue
        try:
            end = content.index("\n---\n", 4)
            fm_orig = yaml.safe_load(content[4:end]) or {}
            body_full = content[end+5:]
        except Exception:
            skipped += 1
            skipped_reasons.append(f"frontmatter parse fail: {sf}")
            continue

        url = str(fm_orig.get("url", ""))
        title = str(fm_orig.get("title", ""))
        slug = str(fm_orig.get("slug", path.stem))
        fetched_method = fm_orig.get("fetched_method", "trafilatura")
        body_len = fm_orig.get("body_len", len(body_full))

        # body 是 # title \n\n## 政策原文\n\n<text>
        body_text = body_full
        m = re.search(r"## 政策原文\n+(.+)", body_full, re.DOTALL)
        if m:
            body_text = m.group(1).strip()

        # 去重检查
        if url in known_urls:
            skipped += 1; continue
        tnorm = re.sub(r"[\s，。、（）()《》\"\']", "", title)
        if tnorm in known_titles:
            skipped += 1; continue
        on = extract_official_number(title) or extract_official_number(body_text[:200])
        if on and on in known_officials:
            skipped += 1; continue

        # 抽取
        region_code, region_name, issuer = detect_region_issuer(url)
        date = extract_date(url, body_text)
        # Fallback 3: official_number 〔YYYY〕N号 → YYYY-01-01
        # (handoff 2026-05-07 #5: 避免 P_1900_*; URL/body 无日期但有文号时用文号年份)
        if not date and on:
            m = re.search(r"〔(\d{4})〕", on)
            if m:
                try:
                    y = int(m.group(1))
                    if 2010 <= y <= 2027:
                        date = f"{y:04d}-01-01"
                except Exception:
                    pass
        pid = gen_pid(date, region_code, slug)
        out_filename = slugify_filename(title, issuer, on, slug)

        # 组 SOP frontmatter
        new_fm = {
            "id": pid,
            "aliases": [pid],
            "title": title,
            "official_number": on or "",
            "issuer": [issuer] if issuer else [],
            "date": date or "",
            "region": {"level": "国家" if region_code == "000000" else "省" if region_code.endswith("0000") else "市",
                       "code": region_code, "name": region_name},
            "type": "policy",
            "provenance": {
                "url": url,
                "fetched_at": fm_orig.get("fetched_at", ""),
                "fetched_method": fetched_method,
                "audit_run": "audit_2026-05-06",
                "candidate_priority": fm_orig.get("candidate_priority", 99),
                "src_count": fm_orig.get("src_count", 1),
            },
            "confidence": "low" if region_code == "000000" and region_name == "未知" else "medium",
        }

        # 写
        out_path = TARGET / out_filename
        if out_path.exists():
            # 已有同名文件,跳
            skipped += 1; continue
        fm_yaml = yaml.dump(new_fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
        new_md = f"---\n{fm_yaml}---\n\n# {title}\n\n## 政策原文\n\n{body_text}\n"
        out_path.write_text(new_md)
        new_files.append({"pid": pid, "filename": out_filename, "url": url})

        known_urls.add(url)
        known_titles.add(tnorm)
        if on: known_officials.add(on)

    # 写 new_pids.txt
    pids_file = ROOT / "_meta" / "audit_2026-05-06" / "new_pids.txt"
    pids_file.write_text("\n".join(f["pid"] for f in new_files))
    new_files_log = ROOT / "_meta" / "audit_2026-05-06" / "new_files.jsonl"
    with new_files_log.open("w") as f:
        for nf in new_files:
            f.write(json.dumps(nf, ensure_ascii=False)+"\n")

    print(f"\n=== Stage F normalize 完成 ===")
    print(f"新入 raw: {len(new_files)}")
    print(f"跳过 (dup/empty/parse-fail): {skipped}")
    print(f"new_pids -> {pids_file}")
    print(f"new_files -> {new_files_log}")


if __name__ == "__main__":
    main()
