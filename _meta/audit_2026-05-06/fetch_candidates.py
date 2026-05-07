#!/usr/bin/env python3
"""
批量抓取候选 URL 正文 (trafilatura + PDF 兜底)
输入: candidates_*.jsonl
输出: 0_raw/policies_staging_2026-05-06/<slug>.md (frontmatter + body)
"""
import json
import os
import re
import sys
import time
import argparse
import hashlib
import requests
import trafilatura
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "0_raw" / "policies_staging_2026-05-06"
STAGING.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

TIMEOUT = 30


def slugify(url, title):
    h = hashlib.sha256((url + "|" + title).encode()).hexdigest()[:8]
    return h


def fetch_one(c):
    url = c["url"]
    title = c["title"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        ct = resp.headers.get("content-type", "").lower()
        if "pdf" in ct or url.lower().endswith(".pdf"):
            try:
                import pdfplumber
                from io import BytesIO
                with pdfplumber.open(BytesIO(resp.content)) as pdf:
                    pages = [p.extract_text() or "" for p in pdf.pages]
                body = "\n\n".join(pages).strip()
                if not body:
                    return {"ok": False, "url": url, "error": "PDF empty after extract"}
                return {"ok": True, "url": url, "body": body, "title": title,
                        "method": "pdfplumber", "content_type": "pdf"}
            except Exception as e:
                return {"ok": False, "url": url, "error": f"PDF parse fail: {e}"}
        # HTML — 用 resp.content (bytes), trafilatura 自检编码; 或显式 detect
        if not resp.content:
            return {"ok": False, "url": url, "error": "empty response"}
        # 强力 encoding detection: 1) html meta charset 2) chardet 3) fallback
        raw = resp.content
        detected_encoding = None
        # 1. 看 HTTP header
        ct_charset = re.search(r"charset=([\w-]+)", resp.headers.get("content-type", ""), re.I)
        if ct_charset:
            detected_encoding = ct_charset.group(1)
        # 2. 看 HTML meta tag (前 4KB)
        if not detected_encoding:
            head = raw[:4096].decode("ascii", errors="ignore")
            m = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', head, re.I)
            if m:
                detected_encoding = m.group(1)
        # 3. chardet 兜底
        if not detected_encoding:
            try:
                import chardet
                d = chardet.detect(raw[:8192])
                if d and d.get("confidence", 0) > 0.7:
                    detected_encoding = d["encoding"]
            except Exception:
                pass
        # 4. 最终兜底
        if not detected_encoding:
            detected_encoding = resp.apparent_encoding or "utf-8"
        # 中国网站常见情况: GB2312 实际上经常是 GBK / GB18030 的子集
        norm_enc = (detected_encoding or "").lower().replace("-", "").replace("_", "")
        if norm_enc in ("gb2312", "gbk"):
            detected_encoding = "gb18030"
        try:
            html_text = raw.decode(detected_encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            html_text = raw.decode("utf-8", errors="replace")
        resp.encoding = detected_encoding
        body = trafilatura.extract(
            html_text,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        # 简单 sanity check: 中文字符占比
        def has_meaningful_chinese(s):
            if not s:
                return False
            chinese = sum(1 for c in s[:500] if '一' <= c <= '鿿')
            return chinese >= 30
        if not body or len(body) < 200 or not has_meaningful_chinese(body):
            # try BS4 fallback
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.content, "html.parser", from_encoding=resp.encoding)
                main = (soup.find("article") or soup.find(id="content")
                        or soup.find(class_=re.compile("article|content|main")))
                if main:
                    body = main.get_text("\n", strip=True)
                else:
                    body = soup.get_text("\n", strip=True)
                if not body or len(body) < 200:
                    return {"ok": False, "url": url, "error": f"body too short ({len(body or '')})"}
                if not has_meaningful_chinese(body):
                    return {"ok": False, "url": url, "error": "encoding garbled (no chinese)"}
                return {"ok": True, "url": url, "body": body, "title": title,
                        "method": "bs4", "content_type": "html"}
            except Exception as e:
                return {"ok": False, "url": url, "error": f"bs4 fail: {e}"}
        return {"ok": True, "url": url, "body": body, "title": title,
                "method": "trafilatura", "content_type": "html"}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)[:200]}


def write_staging(c, fetched):
    """写入 staging 目录: frontmatter + body"""
    if not fetched["ok"]:
        return None
    slug = slugify(c["url"], c["title"])
    path = STAGING / f"{slug}.md"
    fm = {
        "slug": slug,
        "title": c["title"],
        "url": c["url"],
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fetched_method": fetched["method"],
        "content_type": fetched["content_type"],
        "official_number": c.get("official_number") or "",
        "candidate_priority": c.get("priority", 99),
        "src_count": c.get("src_count", 1),
        "sources": c.get("sources", []),
        "body_len": len(fetched["body"]),
    }
    fm_str = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v,(list,dict)) else v}" for k, v in fm.items())
    md = f"---\n{fm_str}\n---\n\n# {c['title']}\n\n## 政策原文\n\n{fetched['body']}\n"
    path.write_text(md)
    return str(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()

    candidates = []
    with open(args.candidates) as f:
        for line in f:
            candidates.append(json.loads(line))
    if args.limit:
        candidates = candidates[: args.limit]
    print(f"Fetching {len(candidates)} URLs, concurrency: {args.concurrency}")
    print(f"Staging: {STAGING}")

    # 抑制 SSL warning
    import urllib3
    urllib3.disable_warnings()

    log_f = open(args.log, "w")
    # B 类修复(2026-05-07,SKILL §A.6):失败 url 同步写到 fetch_failed_for_manual.jsonl
    # 让 P0×P0 fetch 失败可被 audit_alert / diagnose_p0_gaps 发现,走 fallback chain
    failed_manual_path = ROOT / "_meta" / "audit" / "fetch_failed_for_manual.jsonl"
    failed_manual_path.parent.mkdir(parents=True, exist_ok=True)
    failed_manual_f = open(failed_manual_path, "a", encoding="utf-8")
    done = ok = fail = 0
    bytes_total = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(fetch_one, c): c for c in candidates}
        for fut in as_completed(futures):
            c = futures[fut]
            res = fut.result()
            done += 1
            if res["ok"]:
                ok += 1
                path = write_staging(c, res)
                bytes_total += len(res["body"])
                log_line = {"url": c["url"], "ok": True, "method": res["method"],
                            "body_len": len(res["body"]), "staging_path": path}
            else:
                fail += 1
                log_line = {"url": c["url"], "ok": False, "error": res["error"]}
                # 同时写到 manual queue:含 theme/province layer_meta 让 fallback 知道走哪
                manual = {
                    "url": c["url"],
                    "title": c.get("title", ""),
                    "error": res["error"],
                    "layer_meta": c.get("layer_meta", []),
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                }
                failed_manual_f.write(json.dumps(manual, ensure_ascii=False) + "\n")
                failed_manual_f.flush()
            log_f.write(json.dumps(log_line, ensure_ascii=False) + "\n")
            log_f.flush()
            if done % 25 == 0 or done == len(candidates):
                rate = done / (time.time() - t0)
                eta = (len(candidates) - done) / rate if rate else 0
                print(f"  {done}/{len(candidates)} (ok={ok} fail={fail}) "
                      f"avg_body={bytes_total//max(ok,1)}B rate={rate:.1f}/s eta={eta:.0f}s")

    log_f.close()
    failed_manual_f.close()
    print(f"\nDone. ok={ok} fail={fail} time={time.time()-t0:.0f}s")
    print(f"Staging: {STAGING}/")
    print(f"Log: {args.log}")
    if fail:
        print(f"Failed → {failed_manual_path.relative_to(ROOT)} ({fail} url 待 fallback,SKILL §A.6)")


if __name__ == "__main__":
    main()
