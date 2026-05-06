#!/usr/bin/env python3
"""跑 411 query Tavily 矩阵, 并发 5 路."""
import json
import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parents[2]


def run_one(client, q):
    """单 query 调用 Tavily, 返回 result list."""
    try:
        kwargs = dict(
            query=q["query_text"],
            max_results=q.get("max_results", 10),
            search_depth="basic",
        )
        if q.get("include_domains"):
            kwargs["include_domains"] = q["include_domains"]
        r = client.search(**kwargs)
        return {
            "qid": q["qid"],
            "ok": True,
            "results": r.get("results", []),
            "answer": r.get("answer", ""),
        }
    except Exception as e:
        return {"qid": q["qid"], "ok": False, "error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="limit n queries (debug)")
    args = ap.parse_args()

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("ERROR: TAVILY_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    queries = []
    with open(args.queries) as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    if args.limit:
        queries = queries[: args.limit]

    print(f"Total queries: {len(queries)}, concurrency: {args.concurrency}")
    client = TavilyClient(api_key=api_key)

    # 输出 stream
    out_f = open(args.output, "w")
    done = 0
    ok = 0
    fail = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(run_one, client, q): q for q in queries}
        for fut in as_completed(futures):
            q = futures[fut]
            res = fut.result()
            # 把 query meta 拼到 result 一起落盘
            line = {
                "qid": q["qid"],
                "layer": q["layer"],
                "theme_id": q["theme_id"],
                "tier": q["tier"],
                "province_code": q.get("province_code", ""),
                "province_name": q.get("province_name", ""),
                "city_name": q.get("city_name", ""),
                "query_text": q["query_text"],
                "ok": res["ok"],
                "results": res.get("results", []) if res["ok"] else [],
                "error": res.get("error", "") if not res["ok"] else "",
            }
            out_f.write(json.dumps(line, ensure_ascii=False) + "\n")
            out_f.flush()
            done += 1
            if res["ok"]:
                ok += 1
            else:
                fail += 1
            if done % 25 == 0 or done == len(queries):
                rate = done / (time.time() - t0)
                eta = (len(queries) - done) / rate if rate else 0
                print(f"  {done}/{len(queries)} (ok={ok} fail={fail}) rate={rate:.1f}/s eta={eta:.0f}s")

    out_f.close()
    print(f"\nDone. ok={ok} fail={fail} total_time={time.time()-t0:.0f}s")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
