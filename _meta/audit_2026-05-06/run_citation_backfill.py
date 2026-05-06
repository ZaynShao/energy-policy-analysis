#!/usr/bin/env python3
"""跑 citation_gaps 文号补抓: 直接用文号串作 Tavily query"""
import json
import os
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tavily import TavilyClient


def run_one(client, gap):
    try:
        r = client.search(
            query=gap["official_number"],
            max_results=5,
            search_depth="basic",
        )
        return {"ok": True, "gap": gap, "results": r.get("results", [])}
    except Exception as e:
        return {"ok": False, "gap": gap, "error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=2)
    args = ap.parse_args()

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("ERROR: TAVILY_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    gaps = json.load(open(args.gaps))
    if isinstance(gaps, dict):
        gaps = list(gaps.values())
    # 排序: 高引用优先
    gaps.sort(key=lambda g: -g.get("citation_count", 0))
    gaps = gaps[: args.top]
    print(f"Top gaps: {len(gaps)}, concurrency: {args.concurrency}")
    client = TavilyClient(api_key=api_key)

    out_f = open(args.output, "w")
    done = ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(run_one, client, g): g for g in gaps}
        for fut in as_completed(futures):
            res = fut.result()
            g = res["gap"]
            line = {
                "official_number": g["official_number"],
                "citation_count": g.get("citation_count", 0),
                "ok": res["ok"],
                "results": res.get("results", []) if res["ok"] else [],
                "error": res.get("error", ""),
            }
            out_f.write(json.dumps(line, ensure_ascii=False) + "\n")
            out_f.flush()
            done += 1
            if res["ok"]: ok += 1
            else: fail += 1
            if done % 20 == 0 or done == len(gaps):
                rate = done / (time.time() - t0)
                eta = (len(gaps) - done) / rate if rate else 0
                print(f"  {done}/{len(gaps)} (ok={ok} fail={fail}) rate={rate:.1f}/s eta={eta:.0f}s")

    out_f.close()
    print(f"\nDone. ok={ok} fail={fail} total_time={time.time()-t0:.0f}s -> {args.output}")


if __name__ == "__main__":
    main()
