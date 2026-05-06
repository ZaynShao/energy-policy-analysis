"""扫 vault 全部 dangling pid 引用,产 audit 报告"""
from pathlib import Path
import re, json, yaml
from datetime import datetime

VAULT = Path(__file__).resolve().parent.parent.parent
PIDS_FILE = VAULT / "_meta" / "audit" / "vault_pids.txt"

vault_pids = set(PIDS_FILE.read_text(encoding="utf-8").split())

PID_RE = re.compile(r"P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*")
WIKI_RE = re.compile(r"\[\[(P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)(?:\|[^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)

report = {"scan_at": datetime.now().isoformat(), "categories": {}}

# (a) 1_extracted/relations/*.jsonl from/to dangling
cat_a = {"dangling_in_jsonl_field": []}
for jf in (VAULT / "1_extracted" / "relations").glob("*.jsonl"):
    if jf.name.startswith("_"):
        continue
    for ln_no, ln in enumerate(jf.read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        for k in ("from", "to"):
            v = r.get(k)
            if isinstance(v, str) and PID_RE.fullmatch(v) and v not in vault_pids:
                cat_a["dangling_in_jsonl_field"].append({"file": jf.name, "line": ln_no, "field": k, "pid": v})
report["categories"]["dangling_jsonl_from_to"] = cat_a

# (b) 派生层 .md 中的 [[P_xxx]] wiki link 是否都对应 vault
cat_b = {"dangling_wiki_in_derivative_md": []}
for md in VAULT.rglob("*.md"):
    if any(part in md.parts for part in (".git", "_archive", "0_raw")):
        continue
    text = md.read_text(encoding="utf-8", errors="ignore")
    for m in WIKI_RE.finditer(text):
        pid = m.group(1)
        if pid not in vault_pids:
            cat_b["dangling_wiki_in_derivative_md"].append({"file": str(md.relative_to(VAULT)), "pid": pid})
report["categories"]["dangling_wiki_in_md"] = cat_b

# (c) raw 政策 fm.date 异常(未来日期 / 1900 与抓取日不一致)
cat_c = {"future_date": [], "year_1900_with_recent_fetch": []}
NOW_YEAR = datetime.now().year
for p in (VAULT / "0_raw" / "policies").glob("*.md"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    m = FRONTMATTER_RE.match(text)
    if not m:
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        continue
    pid = fm.get("id")
    date = str(fm.get("date", ""))
    fetched = str((fm.get("provenance") or {}).get("fetched_at", ""))
    m2 = re.match(r"(\d{4})", date)
    if m2 and int(m2.group(1)) > NOW_YEAR:
        cat_c["future_date"].append({"pid": pid, "date": date, "filename": p.name})
    if date.startswith("1900") and "2026" in fetched:
        cat_c["year_1900_with_recent_fetch"].append({"pid": pid, "fetched_at": fetched, "filename": p.name})
report["categories"]["raw_fm_date_anomaly"] = cat_c

print(f"\n=== dangling 全景扫报告 ===")
print(f"vault 真实 pid: {len(vault_pids)}")
print(f"\n(a) jsonl from/to dangling: {len(cat_a['dangling_in_jsonl_field'])}")
print(f"(b) 派生 .md wiki link dangling: {len(cat_b['dangling_wiki_in_derivative_md'])}")
print(f"(c) fm.date 未来日期: {len(cat_c['future_date'])}")
print(f"(c) fm.date=1900 + recent fetch: {len(cat_c['year_1900_with_recent_fetch'])}")

out = VAULT / "_meta" / "audit" / "dangling_scan_2026-05-06.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告写到 {out}")
