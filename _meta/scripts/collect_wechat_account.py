#!/usr/bin/env python3
"""
collect_wechat_account.py
P3 — 公众号批量采集 wrapper(搜狗微信搜索 + wechat_article_pipeline)

工作流:
  1. 检查当日 skip flag,存在则退出
  2. 搜狗搜索该公众号(type=2 文章搜索),解析 HTML 提取 mp.weixin.qq.com 链接
  3. 反爬检测:HTTP 5xx / "验证码" / "频繁访问" / "请输入" → abort + 写 skip flag
  4. for each URL(间隔 5 秒):
     - subprocess 调 wechat_article_pipeline.py 抓单篇 → 临时目录
     - 读抓回的 .md,补 frontmatter 字段
     - 移到 0_raw/commentaries/<safe_title>.md(剥 wechat_pipeline 默认的 NN_ 编号目录壳)
  5. 收尾打印总成功 / 跳过 / 失败数

用法:
  python collect_wechat_account.py "中能传媒" --max-articles 20 --business-tag power
  python collect_wechat_account.py "中电联" --dry-run
  python collect_wechat_account.py --self-test     # 不访问网络,只验证 parser

参数:
  account_name        公众号名(必传)
  --max-articles N    最多抓 N 篇,默认 20
  --output-dir DIR    输出目录,默认 0_raw/commentaries/
  --business-tag TAG  power/charging/gas/cross,默认 cross
  --dry-run           只打印计划,不抓
  --self-test         跑 mock test 验证 parser

节流:
  - 搜索页 1 次
  - 每篇 5 秒间隔
  - 反爬触发立即 abort,当日不再试

已知坑:
  - 搜狗 type=2 返回 link?url= 跳转链接,需 requests 跟随重定向拿真 URL
  - 搜狗页面结构每年都可能变,parser 失效时必须人工重写
  - 抓多了会 IP 频控,5 秒节流仅起兜底作用

依赖: stdlib + requests(pipeline 已有)
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# -------- 常量 --------
VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
PIPELINE = VAULT / "_meta/scripts/wechat_article_pipeline.py"
DEFAULT_OUTPUT = VAULT / "0_raw/commentaries"
SCRIPT_DIR = VAULT / "_meta/scripts"
CST = timezone(timedelta(hours=8))

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

ANTI_CRAWL_KEYWORDS = ["验证码", "频繁访问", "请输入", "请刷新", "userverify"]
THROTTLE_SECONDS = 5
BUSINESS_TAGS = {"power", "charging", "gas", "cross"}


# -------- skip flag --------
def skip_flag_path() -> Path:
    today = datetime.now(CST).strftime("%Y-%m-%d")
    return SCRIPT_DIR / f".sogou_skip_{today}.flag"


def write_skip_flag(reason: str) -> None:
    p = skip_flag_path()
    p.write_text(f"{datetime.now(CST).isoformat()}\n{reason}\n", encoding="utf-8")


def is_skipped() -> bool:
    return skip_flag_path().exists()


# -------- 搜索 --------
def build_search_url(account_name: str) -> str:
    q = urllib.parse.quote(account_name, safe="")
    return f"https://weixin.sogou.com/weixin?type=2&query={q}"


def detect_anti_crawl(text: str, status: int) -> str | None:
    """返回 None 表示正常,否则返回反爬原因."""
    if status >= 500:
        return f"HTTP {status}"
    lowered = text.lower()
    for kw in ANTI_CRAWL_KEYWORDS:
        if kw in text or kw in lowered:
            return f"页面含反爬关键词:{kw}"
    return None


# 搜狗 type=2 结果项的常见 HTML 结构(2024-2026 观察):
# <li ... id="sogou_vr_..._box_<i>">
#   <div class="txt-box">
#     <h3><a target="_blank" href="/link?url=<encoded>">标题</a></h3>
#     <p class="txt-info">摘要</p>
#     <div class="s-p" t="时间戳">
#       <a href="..." class="account">公众号名</a>
#     </div>
#   </div>
# </li>
# 用 regex 抽核心三件:link、标题、公众号
RE_RESULT_BLOCK = re.compile(
    r'<li[^>]+id="sogou_vr_[^"]+"[^>]*>(.*?)</li>',
    re.DOTALL,
)
RE_TITLE_LINK = re.compile(
    r'<h3[^>]*>\s*<a[^>]+href="(/link\?url=[^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
RE_ACCOUNT = re.compile(
    r'<span\s+class="all-time-y2"[^>]*>\s*([^<]+?)\s*</span>',
    re.DOTALL,
)
RE_TIME = re.compile(r"timeConvert\('(\d+)'\)")


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def parse_search_html(text: str) -> list[dict]:
    """解析搜狗结果页,返回每条 {sogou_link, title, account, ts}."""
    out = []
    for block in RE_RESULT_BLOCK.findall(text):
        tl = RE_TITLE_LINK.search(block)
        if not tl:
            continue
        sogou_link = html.unescape(tl.group(1))
        title = strip_tags(tl.group(2))
        acc_m = RE_ACCOUNT.search(block)
        account = strip_tags(acc_m.group(1)) if acc_m else ""
        ts_m = RE_TIME.search(block)
        ts = int(ts_m.group(1)) if ts_m else 0
        if not title:
            continue
        out.append({
            "sogou_link": "https://weixin.sogou.com" + sogou_link if sogou_link.startswith("/") else sogou_link,
            "title": title,
            "account": account,
            "ts": ts,
        })
    return out


def resolve_sogou_link(session: requests.Session, sogou_link: str, timeout: int = 30) -> str | None:
    """搜狗 /link?url=xxx 跳转到真 mp.weixin.qq.com 链接.

    搜狗的跳转有两种形态:
      (a) 直接 302 到 mp.weixin.qq.com/s/...
      (b) 返回 HTML 含 JS 还原后的真 URL (反爬强化)
    我们试 (a),失败回退尝试从 HTML 抠 mp 链接.
    """
    try:
        resp = session.get(sogou_link, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return None
    final = resp.url
    if "mp.weixin.qq.com" in final:
        return final
    # 回退:从 HTML 提取 mp 链接
    m = re.search(r'(https?://mp\.weixin\.qq\.com/s[^\s"\'<>]+)', resp.text)
    if m:
        return m.group(1)
    # 还有 JS 拼接形态:url += '...'+'.'+'.'+...,这里不做 JS 解析,留 TODO
    return None


# -------- frontmatter 注入 --------
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def inject_frontmatter(md_path: Path, account: str, business_tag: str) -> None:
    text = md_path.read_text(encoding="utf-8")
    fetched_at = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    new_fm = (
        f"---\n"
        f'source_account: "{account}"\n'
        f"fetched_at: {fetched_at}\n"
        f"commentary_type: 待分类\n"
        f"business_tag: {business_tag}\n"
        f"source: weixin.sogou.com\n"
        f"---\n\n"
    )
    if FM_RE.match(text):
        # 已有 frontmatter,merge 进去(简单方案:在 --- 前插入新字段)
        m = FM_RE.match(text)
        body = text[m.end():]
        merged_block = m.group(1).rstrip() + (
            f"\nsource_account: \"{account}\""
            f"\nfetched_at: {fetched_at}"
            f"\ncommentary_type: 待分类"
            f"\nbusiness_tag: {business_tag}"
            f"\nsource: weixin.sogou.com"
        )
        text = f"---\n{merged_block}\n---\n\n{body.lstrip()}"
    else:
        text = new_fm + text
    md_path.write_text(text, encoding="utf-8")


# -------- 单篇抓取 --------
def fetch_single_article(url: str, tmp_dir: Path, timeout: int = 30) -> Path | None:
    """调 vendored pipeline 抓单篇,返回 .md 路径."""
    cmd = [sys.executable, str(PIPELINE), url, "--output-dir", str(tmp_dir), "--timeout", str(timeout)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    # pipeline 输出 NN_<title>/ 子目录,里面有 .md
    candidates = sorted(tmp_dir.glob("*/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return (name[:100] or "untitled").strip("_") or "untitled"


def move_to_commentaries(src_md: Path, output_dir: Path, title: str) -> Path:
    """剥 NN_ 目录壳,移动 .md(以及同目录其他文件如图片)到扁平 output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = safe_filename(title)
    dest = output_dir / f"{safe}.md"
    # 避免同名覆盖
    n = 2
    while dest.exists():
        dest = output_dir / f"{safe}_{n}.md"
        n += 1
    shutil.move(str(src_md), str(dest))
    # 同目录的图片移到 <safe>_img/
    src_dir = src_md.parent
    others = [p for p in src_dir.iterdir() if p.is_file()]
    if others:
        img_dir = output_dir / f"{safe}_img"
        img_dir.mkdir(exist_ok=True)
        for p in others:
            shutil.move(str(p), str(img_dir / p.name))
    return dest


# -------- 主流程 --------
def run(account_name: str, max_articles: int, output_dir: Path,
        business_tag: str, dry_run: bool) -> dict:
    if is_skipped():
        print(f"[skip] 当日已触发反爬,跳过.flag = {skip_flag_path()}")
        return {"status": "skipped"}

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    search_url = build_search_url(account_name)
    print(f"[search] {search_url}")
    try:
        r = session.get(search_url, timeout=30)
    except requests.RequestException as e:
        print(f"[fatal] 搜索请求失败: {e}")
        write_skip_flag(f"search request failed: {e}")
        return {"status": "search_failed"}

    blocked = detect_anti_crawl(r.text, r.status_code)
    if blocked:
        print(f"[abort] 反爬触发: {blocked}")
        write_skip_flag(blocked)
        return {"status": "blocked", "reason": blocked}

    items = parse_search_html(r.text)
    print(f"[parse] 解析出 {len(items)} 条候选")

    # 公众号名过滤(账号名匹配,避免引用了该号的杂稿)
    items = [it for it in items if account_name in it["account"] or not it["account"]]
    items = items[:max_articles]
    print(f"[filter] 过滤后 {len(items)} 条")

    if dry_run:
        for i, it in enumerate(items, 1):
            print(f"  [{i}] {it['title']} | account={it['account']} | ts={it['ts']}")
        return {"status": "dry_run", "candidates": len(items)}

    tmp_root = Path(f"/tmp/wechat_collect_{account_name}_{int(time.time())}")
    tmp_root.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    for i, it in enumerate(items, 1):
        time.sleep(THROTTLE_SECONDS if i > 1 else 0)
        true_url = resolve_sogou_link(session, it["sogou_link"])
        if not true_url:
            print(f"[{i}/{len(items)}] {it['title']} ... fail (link解析失败)")
            fail += 1
            continue
        md = fetch_single_article(true_url, tmp_root)
        if not md:
            print(f"[{i}/{len(items)}] {it['title']} ... fail (pipeline 抓取失败)")
            fail += 1
            continue
        try:
            dest = move_to_commentaries(md, output_dir, it["title"])
            inject_frontmatter(dest, account_name, business_tag)
            print(f"[{i}/{len(items)}] {it['title']} ... ok → {dest.name}")
            ok += 1
        except Exception as e:
            print(f"[{i}/{len(items)}] {it['title']} ... fail (落地失败: {e})")
            fail += 1

    shutil.rmtree(tmp_root, ignore_errors=True)
    print(f"\n[done] 成功 {ok} / 失败 {fail} / 候选 {len(items)}")
    return {"status": "done", "ok": ok, "fail": fail, "total": len(items)}


# -------- self-test(不访问网络)--------
MOCK_HTML = """
<html><body><div class="news-list">
<ul>
<li id="sogou_vr_11002601_box_0">
  <div class="txt-box">
    <h3><a target="_blank" id="sogou_vr_11002601_title_0" href="/link?url=ABC123_FAKE_URL_1">虚拟电厂市场化路径深度分析</a></h3>
    <p class="txt-info">本文从市场机制、商业模式、政策约束三个维度...</p>
    <div class="s-p" t="1714200000">
      <a href="#" class="account">中能传媒研究院</a>
    </div>
  </div>
</li>
<li id="sogou_vr_11002601_box_1">
  <div class="txt-box">
    <h3><a target="_blank" id="sogou_vr_11002601_title_1" href="/link?url=DEF456_FAKE_URL_2">储能装机预测:2026 年规模与瓶颈</a></h3>
    <p class="txt-info">基于一季度数据...</p>
    <div class="s-p" t="1714000000">
      <a href="#" class="account">中能传媒研究院</a>
    </div>
  </div>
</li>
<li id="sogou_vr_11002601_box_2">
  <div class="txt-box">
    <h3><a target="_blank" id="sogou_vr_11002601_title_2" href="/link?url=GHI789_FAKE_URL_3">电力市场建设回顾与展望</a></h3>
    <p class="txt-info">2026 年是电力市场的关键节点...</p>
    <div class="s-p" t="1713800000">
      <a href="#" class="account">中能传媒研究院</a>
    </div>
  </div>
</li>
</ul></div></body></html>
"""


def self_test() -> int:
    items = parse_search_html(MOCK_HTML)
    expected_titles = [
        "虚拟电厂市场化路径深度分析",
        "储能装机预测:2026 年规模与瓶颈",
        "电力市场建设回顾与展望",
    ]
    if len(items) != 3:
        print(f"[mock test] ✗ expected 3 URLs, got {len(items)}")
        return 1
    for i, (got, want) in enumerate(zip(items, expected_titles)):
        if got["title"] != want:
            print(f"[mock test] ✗ #{i} title mismatch: got '{got['title']}' want '{want}'")
            return 1
        if "FAKE_URL" not in got["sogou_link"]:
            print(f"[mock test] ✗ #{i} link extraction failed: {got['sogou_link']}")
            return 1
        if got["account"] != "中能传媒研究院":
            print(f"[mock test] ✗ #{i} account mismatch: {got['account']}")
            return 1
    print(f"[mock test] ✓ parsed 3 URLs:")
    for it in items:
        print(f"  - {it['title']} | {it['account']} | ts={it['ts']}")
    # 反爬检测正向 case
    if detect_anti_crawl("正常页面无反爬关键字", 200) is not None:
        print("[mock test] ✗ false positive in anti-crawl detect")
        return 1
    if detect_anti_crawl("请输入验证码后继续", 200) is None:
        print("[mock test] ✗ false negative in anti-crawl detect")
        return 1
    if detect_anti_crawl("ok", 503) is None:
        print("[mock test] ✗ HTTP 5xx not detected")
        return 1
    print("[mock test] ✓ anti-crawl detector ok")
    return 0


# -------- CLI --------
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("account_name", nargs="?", help="公众号名")
    p.add_argument("--max-articles", type=int, default=20)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    p.add_argument("--business-tag", default="cross", choices=sorted(BUSINESS_TAGS))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        sys.exit(self_test())

    if not args.account_name:
        p.error("account_name 必传(除非 --self-test)")

    result = run(
        account_name=args.account_name,
        max_articles=args.max_articles,
        output_dir=Path(args.output_dir),
        business_tag=args.business_tag,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
