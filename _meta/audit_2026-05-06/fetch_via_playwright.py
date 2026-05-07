#!/usr/bin/env python3
"""
SSL fallback: 用 playwright/chromium 抓 fetch_candidates.py 失败的 url
（jsdsm.fzggw.jiangsu.gov.cn 等老 TLS 端点 LibreSSL 2.8.3 握不上,
 chromium 内核宽容老 TLS）。

输入: --failed-log _meta/audit_2026-05-06/fetch_p0_refetch.log
      --candidates 原 jsonl(用于回查 title/sources/etc)
      --filter-domain 可选,只跑指定 domain(默认 jsdsm.fzggw.jiangsu.gov.cn)
输出: 0_raw/policies_staging_2026-05-06/<slug>.md(同 fetch_candidates schema)
      新增 log _meta/audit_2026-05-06/fetch_playwright.log
"""
import json, sys, time, hashlib, argparse, asyncio, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "0_raw" / "policies_staging_2026-05-06"
STAGING.mkdir(parents=True, exist_ok=True)


def slugify(url, title):
    return hashlib.sha256((url + "|" + title).encode()).hexdigest()[:8]


def has_meaningful_chinese(s):
    if not s:
        return False
    chinese = sum(1 for c in s[:500] if '一' <= c <= '鿿')
    return chinese >= 30


def write_staging(c, body, method, ctype):
    slug = slugify(c["url"], c["title"])
    path = STAGING / f"{slug}.md"
    fm = {
        "slug": slug,
        "title": c["title"],
        "url": c["url"],
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fetched_method": method,
        "content_type": ctype,
        "official_number": c.get("official_number") or "",
        "candidate_priority": c.get("priority", 99),
        "src_count": c.get("src_count", 1),
        "sources": c.get("sources", []),
        "body_len": len(body),
    }
    fm_str = "\n".join(
        f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v,(list,dict)) else v}"
        for k, v in fm.items()
    )
    md = f"---\n{fm_str}\n---\n\n# {c['title']}\n\n## 政策原文\n\n{body}\n"
    path.write_text(md)
    return str(path)


async def fetch_one(browser, c):
    url = c["url"]
    title = c["title"]
    is_pdf = url.lower().endswith(".pdf")
    page = await browser.new_page(ignore_https_errors=True,
                                  user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
                                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
    try:
        if is_pdf:
            # PDF 直接 raw download via playwright HTTP request API
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context(ignore_https_errors=True)
            req = await ctx.request.get(url, timeout=45000)
            if req.status >= 400:
                return {"ok": False, "url": url, "error": f"HTTP {req.status}"}
            content = await req.body()
            try:
                import pdfplumber
                from io import BytesIO
                with pdfplumber.open(BytesIO(content)) as pdf:
                    pages = [p.extract_text() or "" for p in pdf.pages]
                body = "\n\n".join(pages).strip()
                if not body:
                    return {"ok": False, "url": url, "error": "PDF empty after extract"}
                return {"ok": True, "url": url, "body": body, "method": "playwright_pdf", "ctype": "pdf"}
            except Exception as e:
                return {"ok": False, "url": url, "error": f"PDF parse fail: {e}"}
        else:
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)  # 静态页等渲染
            html = await page.content()
            try:
                import trafilatura
                body = trafilatura.extract(
                    html, output_format="markdown",
                    include_comments=False, include_tables=True, no_fallback=False,
                )
            except Exception:
                body = None
            if not body or len(body) < 200 or not has_meaningful_chinese(body):
                # BS4 fallback
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    main = (soup.find("article") or soup.find(id="content")
                            or soup.find(class_=re.compile("article|content|main")))
                    body = main.get_text("\n", strip=True) if main else soup.get_text("\n", strip=True)
                    if not body or len(body) < 200:
                        return {"ok": False, "url": url, "error": f"body too short ({len(body or '')})"}
                    if not has_meaningful_chinese(body):
                        return {"ok": False, "url": url, "error": "encoding garbled"}
                    return {"ok": True, "url": url, "body": body, "method": "playwright_bs4", "ctype": "html"}
                except Exception as e:
                    return {"ok": False, "url": url, "error": f"bs4 fail: {e}"}
            return {"ok": True, "url": url, "body": body, "method": "playwright_trafilatura", "ctype": "html"}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)[:200]}
    finally:
        await page.close()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--failed-log", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--filter-domain", default="")
    ap.add_argument("--log", required=True)
    args = ap.parse_args()

    # 读 failed log → set of failed urls
    failed_urls = set()
    with open(args.failed_log) as f:
        for line in f:
            try:
                r = json.loads(line)
                if not r.get("ok") and (not args.filter_domain or args.filter_domain in r["url"]):
                    failed_urls.add(r["url"])
            except: pass

    # 从 candidates 拿完整 record
    target = []
    with open(args.candidates) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r["url"] in failed_urls:
                    target.append(r)
            except: pass

    print(f"Playwright fetch: {len(target)} urls (filter: {args.filter_domain or '<none>'})")

    from playwright.async_api import async_playwright
    import os
    proxy_url = os.environ.get("PLAYWRIGHT_PROXY") or os.environ.get("https_proxy") or os.environ.get("http_proxy")
    log_f = open(args.log, "w")
    ok = fail = 0
    launch_args = ["--ignore-certificate-errors", "--ignore-ssl-errors"]
    launch_kwargs = {"headless": True, "args": launch_args}
    if proxy_url:
        launch_kwargs["proxy"] = {"server": proxy_url}
        print(f"Using proxy: {proxy_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        # 串行(老 TLS server 怕并发)
        for c in target:
            res = await fetch_one(browser, c)
            if res["ok"]:
                ok += 1
                path = write_staging(c, res["body"], res["method"], res["ctype"])
                log_f.write(json.dumps({"url": c["url"], "ok": True, "method": res["method"],
                                        "body_len": len(res["body"]), "staging_path": path}, ensure_ascii=False) + "\n")
                print(f"  OK  {c['url'][:80]}  ({len(res['body'])}B)")
            else:
                fail += 1
                log_f.write(json.dumps({"url": c["url"], "ok": False, "error": res["error"]}, ensure_ascii=False) + "\n")
                print(f"  FAIL {c['url'][:80]}  → {res['error'][:80]}")
        await browser.close()
    log_f.close()
    print(f"\nDone. ok={ok} fail={fail}")


if __name__ == "__main__":
    asyncio.run(main())
