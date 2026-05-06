#!/usr/bin/env python3
"""聚合三路 Tavily 结果, 去重, 与 vault 已收交叉, 生成候选 URL 池"""
import json
import os
import re
import argparse
import yaml
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def parse_frontmatter(content):
    if not content.startswith("---\n"):
        return {}
    try:
        end = content.index("\n---\n", 4)
        return yaml.safe_load(content[4:end]) or {}
    except Exception:
        return {}


def load_vault_known():
    """vault 已收政策的: official_number, title, source_url"""
    known_official = set()
    known_titles = set()
    known_urls = set()
    raw_dir = ROOT / "0_raw" / "policies"
    for f in os.listdir(raw_dir):
        if not f.endswith(".md"):
            continue
        try:
            content = (raw_dir / f).read_text()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        on = fm.get("official_number") or fm.get("official")
        if on:
            known_official.add(re.sub(r"\s+", "", str(on)))
        title = fm.get("title", "")
        if title:
            # 标题哈希(去标点空格)
            tnorm = re.sub(r"[\s，。、（）()《》\"\']", "", title.strip())
            known_titles.add(tnorm)
        prov = fm.get("provenance", {}) or {}
        url = prov.get("url") or prov.get("source_url") or ""
        if url:
            known_urls.add(url.strip())
    return known_official, known_titles, known_urls


# 政策网站白名单 (gov / 政府门户 + 已知合规媒体)
GOV_DOMAINS = {
    "gov.cn", "miit.gov.cn", "ndrc.gov.cn", "nea.gov.cn", "mofcom.gov.cn",
    "mof.gov.cn", "mohurd.gov.cn", "mee.gov.cn", "samr.gov.cn",
}
# 子域名识别: *.gov.cn 一概认 governmental
def is_gov(url):
    try:
        host = urlparse(url).hostname or ""
        if host.endswith(".gov.cn") or host == "gov.cn":
            return True
        for d in GOV_DOMAINS:
            if host == d or host.endswith("." + d):
                return True
    except Exception:
        pass
    return False


# 非政府但媒体合规(白名单),后续 SOP 升级再扩充
ALLOWED_MEDIA = {
    "bjx.com.cn",   # 北极星电力网
    "in-en.com",    # 国际能源网
    "cec.org.cn",   # 中电联
    "chinaelc.cn",  # 中能传媒
    "ditan.com",    # 低碳网
    "sasac.gov.cn",
    "china5e.com",
    "xhby.net",     # 新华日报
}


def is_media_allowed(url):
    try:
        host = urlparse(url).hostname or ""
        for d in ALLOWED_MEDIA:
            if host == d or host.endswith("." + d):
                return True
    except Exception:
        pass
    return False


def extract_official_from_text(s):
    if not s:
        return None
    m = re.search(r"[一-龥A-Z]{2,8}?〔(\d{4})〕\s*(\d{1,5})\s*号", s)
    if m:
        return re.sub(r"\s+", "", m.group(0))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tavily", required=True)
    ap.add_argument("--promotion", default="")
    ap.add_argument("--citation", default="")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    print("Loading vault known set...")
    known_official, known_titles, known_urls = load_vault_known()
    print(f"  vault known: {len(known_official)} officials, {len(known_titles)} titles, {len(known_urls)} urls")

    candidates = {}  # url -> meta

    def add_candidate(item, source, layer_meta):
        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        content = item.get("content", "")
        if not url or not title:
            return
        if url in known_urls:
            return
        # 标题哈希去重
        tnorm = re.sub(r"[\s，。、（）()《》\"\']", "", title)
        if tnorm in known_titles:
            return
        # 文号去重
        on = extract_official_from_text(title) or extract_official_from_text(content[:200])
        if on and on in known_official:
            return
        # 域名过滤
        gov = is_gov(url)
        media = is_media_allowed(url)
        if not (gov or media):
            return
        # 已加过的: 累加 source
        if url in candidates:
            candidates[url]["sources"].append(source)
            candidates[url]["layer_meta"].append(layer_meta)
        else:
            candidates[url] = {
                "url": url,
                "title": title,
                "content_snippet": content[:300],
                "score": item.get("score", 0),
                "is_gov": gov,
                "is_media": media,
                "official_number": on,
                "sources": [source],
                "layer_meta": [layer_meta],
            }

    # Tavily 矩阵
    with open(args.tavily) as f:
        for line in f:
            r = json.loads(line)
            if not r["ok"]:
                continue
            layer_meta = {
                "qid": r["qid"],
                "layer": r["layer"],
                "theme_id": r["theme_id"],
                "tier": r["tier"],
                "province_code": r.get("province_code", ""),
                "city_name": r.get("city_name", ""),
            }
            for item in r["results"]:
                add_candidate(item, "tavily_matrix", layer_meta)
    print(f"After tavily_matrix: {len(candidates)} candidates")

    # 候选晋升
    if args.promotion and Path(args.promotion).exists():
        with open(args.promotion) as f:
            for line in f:
                r = json.loads(line)
                if not r.get("ok"):
                    continue
                layer_meta = {"layer": "promotion", "domain": r.get("domain", ""),
                              "theme_id": r.get("theme_id", ""),
                              "province_code": r.get("province_code", "")}
                for item in r.get("results", []):
                    add_candidate(item, "candidate_promotion", layer_meta)
        print(f"After promotion: {len(candidates)} candidates")

    # 引用补抓
    if args.citation and Path(args.citation).exists():
        with open(args.citation) as f:
            for line in f:
                r = json.loads(line)
                if not r.get("ok"):
                    continue
                layer_meta = {"layer": "citation",
                              "official_number": r.get("official_number", ""),
                              "citation_count": r.get("citation_count", 0)}
                for item in r.get("results", []):
                    add_candidate(item, "citation_backfill", layer_meta)
        print(f"After citation: {len(candidates)} candidates")

    # 写出
    out_list = list(candidates.values())
    out_list.sort(key=lambda c: -c["score"] if c["score"] else 0)
    with open(args.output, "w") as f:
        for c in out_list:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 统计
    gov_n = sum(1 for c in out_list if c["is_gov"])
    media_n = sum(1 for c in out_list if c["is_media"])
    multi_source = sum(1 for c in out_list if len(c["sources"]) >= 2)
    print(f"\n=== 候选 URL 池: {len(out_list)} ===")
    print(f"  gov 域名:    {gov_n}")
    print(f"  media 白名单: {media_n}")
    print(f"  多路命中:    {multi_source}")
    print(f"  输出: {args.output}")


if __name__ == "__main__":
    main()
