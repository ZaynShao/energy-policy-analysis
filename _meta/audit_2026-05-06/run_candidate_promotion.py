#!/usr/bin/env python3
"""跑候选渠道晋升: 156 个 site: filter Tavily 检索"""
import json
import os
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tavily import TavilyClient


def run_one(client, t):
    try:
        r = client.search(
            query=t["tavily_query"],
            max_results=t.get("max_results", 5),
            search_depth="basic",
        )
        return {"ok": True, "task": t, "results": r.get("results", [])}
    except Exception as e:
        return {"ok": False, "task": t, "error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--concurrency", type=int, default=2)
    args = ap.parse_args()

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("ERROR: TAVILY_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    tasks = []
    with open(args.tasks) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    print(f"Tasks: {len(tasks)}, concurrency: {args.concurrency}")
    client = TavilyClient(api_key=api_key)

    out_f = open(args.output, "w")
    done = ok = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(run_one, client, t): t for t in tasks}
        for fut in as_completed(futures):
            res = fut.result()
            t = res["task"]
            line = {
                "domain": t["domain"],
                "province_code": t["province_code"],
                "province_name": t["province_name"],
                "theme_id": t["theme_id"],
                "query": t["tavily_query"],
                "ok": res["ok"],
                "results": res.get("results", []) if res["ok"] else [],
                "error": res.get("error", ""),
            }
            out_f.write(json.dumps(line, ensure_ascii=False) + "\n")
            out_f.flush()
            done += 1
            if res["ok"]: ok += 1
            else: fail += 1
            if done % 20 == 0 or done == len(tasks):
                rate = done / (time.time() - t0)
                eta = (len(tasks) - done) / rate if rate else 0
                print(f"  {done}/{len(tasks)} (ok={ok} fail={fail}) rate={rate:.1f}/s eta={eta:.0f}s")

    out_f.close()
    print(f"\nDone. ok={ok} fail={fail} total_time={time.time()-t0:.0f}s -> {args.output}")


if __name__ == "__main__":
    main()
