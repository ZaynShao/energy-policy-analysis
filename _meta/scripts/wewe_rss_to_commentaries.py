#!/usr/bin/env python3
"""
wewe_rss_to_commentaries.py
P3 主路径 — wewe-rss(微信读书) → 0_raw/commentaries/ 同步

工作流:
  1. GET http://localhost:4000/feeds/all.json 拉全部订阅源 + 全文
     (wewe-rss 已在后台预拉好正文存 SQLite,此处从本地读 0 次微信 API)
  2. JSON Feed 1.1 格式解析,逐条:
     - URL 去重(扫 0_raw 现有 source_url)
     - HTML → Markdown(复用 wechat_article_pipeline 的 parser)
     - 落 0_raw/commentaries/<safe_title>.md
     - 加 frontmatter(source_account / business_tag / commentary_type=待分类)
  3. 进度 + 收尾按号统计

用法:
  python wewe_rss_to_commentaries.py --dry-run                  # 预览
  python wewe_rss_to_commentaries.py                            # 全量同步
  python wewe_rss_to_commentaries.py --since 2026-04-01         # 增量
  python wewe_rss_to_commentaries.py --limit 200                # 每次最多拉 N 条

依赖: stdlib + requests + wechat_article_pipeline.py(同目录已 vendor)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
DEFAULT_OUTPUT = VAULT / "0_raw/commentaries"
DEFAULT_BASE = "http://localhost:4000"
SCRIPT_DIR = VAULT / "_meta/scripts"
CST = timezone(timedelta(hours=8))

# 公众号 → 业务线映射(已订阅 8 + 待订阅 9)
ACCOUNT_BUSINESS_MAP = {
    # 第一批 8 个(精确名按 wewe-rss 实际显示)
    "中能传媒研究院": "power",
    "中国电力企业联合会": "power",
    "储能与电力市场": "power",
    "电力市场与价格洞察": "power",
    "高工储能": "power",
    "国网能源研究院有限公司": "power",
    "落基山研究所": "cross",
    "电动汽车观察家": "charging",
    # 第二批 9 个(实际公众号名,2026-04-29 实测对齐)
    "中国石油经济技术研究院": "gas",
    "中石油经研院 智库研究中心": "gas",         # 实际订阅名
    # "卓创资讯": "gas",                       # DEPRECATED 2026-04-29 关联率 3% 商品行情为主,A1 R2 已标历史
    # "隆众资讯": "gas",                       # DEPRECATED 2026-04-29
    # "隆众资讯订阅号": "gas",                 # DEPRECATED 2026-04-29 关联率 0.5% 化工油气日度行情
    "36碳": "cross",
    "金杜律师事务所": "cross",
    "金杜研究": "cross",                       # 实际订阅名
    "中央财经大学绿色金融国际研究院": "cross",
    "中央财经大学IIGF": "cross",
    "中国(深圳)综合开发研究院": "cross",
    "综合开发研究院": "cross",                 # 实际订阅名
    "人民网研究院": "cross",                   # ⚠️ 观察期 2026-04-29~2026-05-29 关联率 3%,A1 R2 已标历史 + B1 黑名单兜底,1 月后 review 是否退订
    "能源评论": "cross",
    "能源评论•首席能源观": "cross",            # 实际订阅名
}
DEFAULT_BUSINESS = "cross"

# 标题噪音黑名单(2026-04-28 实测分布定的中度版,粗过滤)
# 命中 → wrapper 直接跳过,不入库。剩下的进库 + 后续 audit + LLM 精判 A 类
# 2026-04-29 + 共享 A1/B1 行情/月报/法律/化工正则(_noise_patterns.JUNK_TITLE_REGEXES)
from _noise_patterns import JUNK_TITLE_REGEXES  # noqa: E402

NOISE_PATTERNS = [
    # === 行政通报型(高确定 C) ===
    (re.compile(r"召开|工作会议|工作会|座谈会|联席会|协调会|动员会|交流会|会议召开|圆满举办"), "会议通报"),
    (re.compile(r"第\s*\d+\s*期|指数第|CECI|CNESI|CNECI|周报"), "周期指数/周报"),
    (re.compile(r"招聘|招募|招标公告|公开招"), "招聘/招标公告"),
    (re.compile(r"喜报|斩获|获奖|获得.*奖|首次.*奖"), "喜报"),
    (re.compile(r"党委|党支部|党课|党建|党组学习|主题教育|不忘初心|学习贯彻|理论中心组"), "党建/学习"),
    (re.compile(r"庆祝|揭牌|挂牌|启动仪式|开业|开班|签约|授牌"), "仪式/活动"),
    # 注意:"调研"要收紧,避免误伤"深度调研"类原创
    (re.compile(r"领导.*调研|赴.*调研|实地调研|走访|慰问|视察|检查工作"), "调研走访"),
    (re.compile(r"@所有人|议程|预告|敬请关注|相约|邀请函|报名|大会|博览会|展览会|论坛"), "活动预告"),
    (re.compile(r"贯彻|落实.*精神|学.*讲话|领导.*重要"), "贯彻精神"),
    (re.compile(r"先进典型|事迹|榜样|表彰|劳模"), "宣传典型"),
    # === 转发型栏目(2026-04-28 中度版新增) ===
    (re.compile(r"^\s*【\s*媒体报道\s*】"), "转发媒体"),
    (re.compile(r"^\s*行业要闻\s*[|｜]"), "转发行业要闻"),
    (re.compile(r"招标[^a-zA-Z]|招标$|招标投标|招标公告|招标采购"), "商业招标"),
    # === 行情/月报/法律/化工(2026-04-29 共享自 _noise_patterns,A1/B1 同源) ===
    *JUNK_TITLE_REGEXES,
]


def title_noise_bucket(title: str) -> str | None:
    """返回 None = 不是噪音(放行);返回 str = 噪音类型(跳过)。"""
    if not title:
        return None
    for pat, name in NOISE_PATTERNS:
        if pat.search(title):
            return name
    return None


# 复用 vendored pipeline 的 HTML → Markdown parser
sys.path.insert(0, str(SCRIPT_DIR))
from wechat_article_pipeline import HTMLToMarkdownParser  # noqa: E402


class NoOpImageDownloader:
    """parser 需要一个 downloader 但我们不下图(wewe-rss 已含全文 HTML),
    返回 None 让 parser 用原 src URL。"""
    def __init__(self):
        self.image_index = 0

    def download(self, source):
        self.image_index += 1
        return None


def html_to_markdown(content_html: str) -> str:
    parser = HTMLToMarkdownParser(NoOpImageDownloader())
    parser.feed(content_html)
    return parser.get_markdown()


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return (name[:100] or "untitled").strip("_") or "untitled"


# 扫现有 commentaries 提取已抓 URL(去重用)
URL_RE = re.compile(r'^source_url:\s*["\']?([^"\'\n]+)["\']?\s*$', re.M)


def collect_existing_urls(output_dir: Path) -> set[str]:
    """扫 commentaries 当前 + .archive 历史 (避免归档文件被重新拉回)."""
    urls = set()
    paths_to_scan = [output_dir]
    archive_root = output_dir.parent / ".archive" / "commentaries"
    if archive_root.exists():
        for d in archive_root.iterdir():
            if d.is_dir():
                paths_to_scan.append(d)
    for p in paths_to_scan:
        if not p.exists():
            continue
        for f in p.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")[:3000]
                m = URL_RE.search(text)
                if m:
                    urls.add(m.group(1).strip())
            except Exception:
                continue
    return urls


def fetch_feed(base_url: str, limit: int = 500, timeout: int = 300) -> dict:
    """/feeds 路径无需 auth_code(README 明确说明)。"""
    url = f"{base_url}/feeds/all.json"
    r = requests.get(url, params={"limit": limit}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def yaml_escape(s: str) -> str:
    """frontmatter 里把 " 转 ' 避免 YAML 引号嵌套报错。"""
    return s.replace('"', "'").strip()


def write_item(item: dict, output_dir: Path, business_tag: str) -> Path | None:
    title = (item.get("title") or "").strip() or "untitled"
    url = (item.get("url") or "").strip()
    content_html = item.get("content_html") or item.get("content_text") or ""
    if not content_html.strip():
        return None
    # wewe-rss 用 date_modified(单数) 不是 date_published
    date_published = (item.get("date_modified") or item.get("date_published") or "")[:10]

    # wewe-rss 用单数 author 不是 authors[](JSON Feed 1.0 风格)
    author = item.get("author") or {}
    if isinstance(author, list):
        author = author[0] if author else {}
    account = (author.get("name") or "") if isinstance(author, dict) else ""

    md_body = html_to_markdown(content_html)
    fetched_at = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    fm = (
        "---\n"
        f'title: "{yaml_escape(title)}"\n'
        f'source_account: "{yaml_escape(account)}"\n'
        f'source_url: "{url}"\n'
        f"date_published: {date_published}\n"
        f"fetched_at: {fetched_at}\n"
        f"commentary_type: 待分类\n"
        f"business_tag: {business_tag}\n"
        f"source: wewe-rss\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{md_body}\n"
    )

    safe = safe_filename(title)
    dest = output_dir / f"{safe}.md"
    n = 2
    while dest.exists():
        dest = output_dir / f"{safe}_{n}.md"
        n += 1
    dest.write_text(fm, encoding="utf-8")
    return dest


def run_dry_run_against_existing(commentaries_dir: Path) -> None:
    """扫现有 commentaries title 跑新 NOISE_PATTERNS,验证黑名单升级是否合理。

    输出:命中数 / 各 bucket 分布 / FP(命中但已 linked)/ 抽样
    """
    import yaml as _yaml

    fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    files = sorted(commentaries_dir.glob("*.md"))
    total = len(files)
    hits = 0
    bucket_counts: dict[str, int] = {}
    fp_count = 0
    fp_samples: list[tuple[str, str, str]] = []
    hit_samples: dict[str, list[tuple[str, str]]] = {}

    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        m = fm_re.match(text)
        if not m:
            continue
        try:
            fm = _yaml.safe_load(m.group(1)) or {}
        except _yaml.YAMLError:
            continue
        title = (fm.get("title") or f.stem).strip()
        bucket = title_noise_bucket(title)
        if not bucket:
            continue
        hits += 1
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        is_linked = fm.get("related_policy") not in (None, "", [], "~")
        if is_linked:
            fp_count += 1
            if len(fp_samples) < 10:
                fp_samples.append((f.name, fm.get("source_account") or "", title))
        else:
            samples = hit_samples.setdefault(bucket, [])
            if len(samples) < 3:
                samples.append((fm.get("source_account") or "", title))

    print(f"\n=== dry-run against existing {total} commentaries ===")
    print(f"命中 NOISE_PATTERNS: {hits} / {total} = {hits/total*100:.1f}%")
    print(f"FP(命中 但 已 linked): {fp_count} / {hits} = {fp_count/max(hits,1)*100:.1f}%")
    print(f"  门槛: 命中 ≥ 20%(≥{int(total*0.20)})且 FP ≤ 5%")
    print("\n  各 bucket 分布:")
    for name, n in sorted(bucket_counts.items(), key=lambda x: -x[1]):
        print(f"    {name}: {n}")

    if fp_samples:
        print("\n  FP 抽样(命中但已 linked,可能误伤):")
        for fname, acc, title in fp_samples:
            print(f"    • [{acc}] {title[:80]}")

    print("\n  命中抽样(按 bucket 各 3 条,未 linked):")
    for bucket, sams in sorted(hit_samples.items()):
        if not sams:
            continue
        print(f"    [{bucket}]")
        for acc, title in sams:
            print(f"      • [{acc}] {title[:80]}")


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--base-url", default=DEFAULT_BASE)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    p.add_argument("--since", default=None, help="YYYY-MM-DD,只同步此日期之后")
    p.add_argument("--limit", type=int, default=500, help="每次拉的上限(>500 易超时)")
    p.add_argument("--timeout", type=int, default=300, help="HTTP 超时秒数")
    p.add_argument("--dry-run", action="store_true", help="只打印不写文件")
    p.add_argument("--no-filter", action="store_true", help="禁用标题噪音黑名单(不推荐)")
    p.add_argument(
        "--dry-run-against-existing",
        action="store_true",
        help="不连 feed,扫现有 0_raw/commentaries/ 跑新 NOISE_PATTERNS,统计命中数 + FP",
    )
    args = p.parse_args()

    if args.dry_run_against_existing:
        run_dry_run_against_existing(Path(args.output_dir))
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[fetch] {args.base_url}/feeds/all.json (limit={args.limit}, timeout={args.timeout}s)")
    try:
        feed = fetch_feed(args.base_url, args.limit, args.timeout)
    except requests.RequestException as e:
        print(f"[fatal] 拉 feed 失败: {e}")
        sys.exit(1)
    items = feed.get("items") or []
    print(f"[fetch] {len(items)} items in feed")

    existing_urls = collect_existing_urls(output_dir)
    print(f"[dedup] {len(existing_urls)} existing source_url in vault")

    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=CST)

    written = skipped_dup = skipped_old = skipped_empty = errs = 0
    skipped_noise = 0
    noise_buckets: dict[str, int] = {}
    by_account: dict[str, int] = {}

    for item in items:
        url = (item.get("url") or "").strip()
        if url and url in existing_urls:
            skipped_dup += 1
            continue

        # 标题噪音黑名单(粗过滤,默认开)
        if not args.no_filter:
            title = (item.get("title") or "").strip()
            bucket = title_noise_bucket(title)
            if bucket:
                skipped_noise += 1
                noise_buckets[bucket] = noise_buckets.get(bucket, 0) + 1
                continue

        if since_dt:
            dp = item.get("date_modified") or item.get("date_published")
            if dp:
                try:
                    iso = dp.replace("Z", "+00:00")
                    item_dt = datetime.fromisoformat(iso)
                    if item_dt < since_dt:
                        skipped_old += 1
                        continue
                except ValueError:
                    pass

        author = item.get("author") or {}
        if isinstance(author, list):
            author = author[0] if author else {}
        account = (author.get("name") or "") if isinstance(author, dict) else ""
        business = ACCOUNT_BUSINESS_MAP.get(account, DEFAULT_BUSINESS)

        if not (item.get("content_html") or item.get("content_text")):
            skipped_empty += 1
            continue

        if args.dry_run:
            title = (item.get("title") or "")[:60]
            print(f"  [+] {title} | acc={account} | biz={business}")
            written += 1
            by_account[account] = by_account.get(account, 0) + 1
            continue

        try:
            dest = write_item(item, output_dir, business)
            if dest:
                written += 1
                by_account[account] = by_account.get(account, 0) + 1
                if written % 10 == 0:
                    print(f"  [{written}] {dest.name[:60]}")
        except Exception as e:
            errs += 1
            print(f"  [err] {(item.get('title') or '')[:50]} → {e}")

    print(
        f"\n[done] wrote={written} dup_skip={skipped_dup} "
        f"noise_skip={skipped_noise} too_old={skipped_old} "
        f"empty={skipped_empty} err={errs}"
    )
    if noise_buckets:
        print("[noise filter]")
        for name, n in sorted(noise_buckets.items(), key=lambda x: -x[1]):
            print(f"  - {name}: {n}")
    if by_account:
        print("[by account]")
        for acc, n in sorted(by_account.items(), key=lambda x: -x[1]):
            tag = ACCOUNT_BUSINESS_MAP.get(acc, DEFAULT_BUSINESS)
            print(f"  - {acc} [{tag}]: {n}")


if __name__ == "__main__":
    main()
