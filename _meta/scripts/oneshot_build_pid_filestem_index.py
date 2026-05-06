"""扫 0_raw/policies/ 全部 fm.id + 文件名,建 vault_pids + pid_to_filestem 索引"""
from pathlib import Path
import re, json, yaml

VAULT = Path(__file__).resolve().parent.parent.parent
RAW = VAULT / "0_raw" / "policies"
OUT_PIDS = VAULT / "_meta" / "audit" / "vault_pids.txt"
OUT_MAP = VAULT / "_meta" / "audit" / "pid_to_filestem.json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)

vault_pids = set()
pid_to_filestem = {}
for p in RAW.glob("*.md"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    m = FRONTMATTER_RE.match(text)
    if not m:
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        continue
    pid = fm.get("id")
    if isinstance(pid, str):
        vault_pids.add(pid)
        pid_to_filestem[pid] = p.stem

OUT_PIDS.write_text("\n".join(sorted(vault_pids)) + "\n", encoding="utf-8")
OUT_MAP.write_text(json.dumps(pid_to_filestem, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"vault_pids: {len(vault_pids)} → {OUT_PIDS}")
print(f"pid_to_filestem: {len(pid_to_filestem)} → {OUT_MAP}")
