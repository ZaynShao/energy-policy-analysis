#!/usr/bin/env python3
"""
refetch_low_quality.py
扫 0_raw/policies/ 中 body_len < 3000 的政策,用 requests + trafilatura 重抓。

策略:
  - 读 provenance.url
  - requests.get + UA spoof + verify=False(gov.cn 偶尔证书问题)
  - trafilatura.extract → 新正文
  - 如果新正文显著大于旧正文(≥ 1.5x 且 ≥ 3KB)→ replace 正文(保留 frontmatter)
  - 否则 → 标 refetch_failed,保持原状(weekly lint 持续 flag)

输出:
  - _meta/refetch_low_quality_log.jsonl
  - 政策文件正文被原地更新(frontmatter 不动)
"""

import re
import json
import yaml
import time
from pathlib import Path
from datetime import datetime
import urllib3
import requests
import trafilatura

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
POLICIES = VAULT / "0_raw" / "policies"
LOG = VAULT / "_meta" / "refetch_low_quality_log.jsonl"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LOW_THRESHOLD = 3000

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def fetch(url):
    """返回 (extracted_text or None, error or None)"""
    if not url:
        return None, "empty_url"
    try:
        r = requests.get(url, headers={"User-Agent": UA},
                         timeout=20, verify=False, allow_redirects=True)
        if r.status_code != 200:
            return None, f"status_{r.status_code}"
        # 自动检测编码
        if not r.encoding or r.encoding == "ISO-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        text = trafilatura.extract(html,
                                   include_comments=False,
                                   include_tables=True,
                                   no_fallback=False,
                                   favor_recall=True)
        if not text:
            return None, "trafilatura_empty"
        return text, None
    except requests.RequestException as e:
        return None, f"request_err: {str(e)[:50]}"
    except Exception as e:
        return None, f"unknown_err: {str(e)[:50]}"


def main():
    print(f"Scanning low-quality policies (body_len < {LOW_THRESHOLD})...")
    targets = []
    for f in sorted(POLICIES.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_fm(text)
        if fm is None:
            continue
        body_len = len(body)
        if body_len >= LOW_THRESHOLD:
            continue
        url = (fm.get("provenance") or {}).get("url", "")
        if not url:
            continue
        targets.append({
            "path": f,
            "filename": f.name,
            "pid": fm.get("id", ""),
            "url": url,
            "old_body_len": body_len,
            "fm": fm,
            "body": body,
        })

    print(f"  {len(targets)} candidates for refetch")
    print()

    LOG.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(LOG, "w", encoding="utf-8")

    success = 0
    fail = 0
    no_improve = 0

    for i, t in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {t['pid'][:35]} ({t['old_body_len']} bytes)")
        new_text, err = fetch(t["url"])
        result = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "pid": t["pid"],
            "filename": t["filename"],
            "url": t["url"],
            "old_body_len": t["old_body_len"],
        }
        if err:
            result["status"] = "fail"
            result["error"] = err
            fail += 1
            print(f"  → FAIL: {err}")
        else:
            new_len = len(new_text)
            result["new_body_len"] = new_len
            if new_len >= LOW_THRESHOLD and new_len >= t["old_body_len"] * 1.5:
                # 显著改善 → 替换
                # 保留 frontmatter,只换正文
                # 在新正文头部加结构化字段(标题/文号/日期/URL)以保持文件可读性
                title = t["fm"].get("title", "")
                official = t["fm"].get("official_number", "") or ""
                date = t["fm"].get("date", "") or ""
                issuers = t["fm"].get("issuer", []) or []
                issuer_str = " / ".join(issuers) if issuers else ""

                header_lines = [f"# {title}", ""]
                if official:
                    header_lines.append(f"**文号**: {official}  ")
                if issuer_str:
                    header_lines.append(f"**发文机构**: {issuer_str}  ")
                if date:
                    header_lines.append(f"**发布日期**: {date}  ")
                header_lines.append(f"**来源**: {t['url']}")
                header_lines.append("")
                header_lines.append("## 政策原文")
                header_lines.append("")
                new_body = "\n".join(header_lines) + new_text + "\n"

                # 写回(frontmatter 保持不变,正文替换)
                fm_yaml = yaml.dump(t["fm"], allow_unicode=True,
                                    default_flow_style=False, sort_keys=False)
                t["path"].write_text(
                    "---\n" + fm_yaml + "---\n" + new_body,
                    encoding="utf-8")
                result["status"] = "success"
                result["improvement"] = f"{t['old_body_len']} → {new_len}"
                success += 1
                print(f"  → SUCCESS: {t['old_body_len']} → {new_len}")
            else:
                result["status"] = "no_improvement"
                result["new_body_len"] = new_len
                no_improve += 1
                print(f"  → NO IMPROVEMENT: new {new_len} bytes (need ≥{LOW_THRESHOLD} & ≥1.5x)")

        log_f.write(json.dumps(result, ensure_ascii=False) + "\n")
        log_f.flush()

        # 节流:不同站点 1.5s 间隔
        if i < len(targets):
            time.sleep(1.5)

    log_f.close()
    print()
    print(f"=== Done ===")
    print(f"  success: {success}")
    print(f"  no improvement: {no_improve}")
    print(f"  fail: {fail}")
    print(f"  log: {LOG}")


if __name__ == "__main__":
    main()
