"""把派生层 .md 中的 [[P_xxx]] 转为 [[file_stem|P_xxx]] 显式格式"""
from pathlib import Path
import re, json

VAULT = Path(__file__).resolve().parent.parent.parent
MAP_FILE = VAULT / "_meta" / "audit" / "pid_to_filestem.json"

pid_to_filestem = json.loads(MAP_FILE.read_text(encoding="utf-8"))

# 匹配 [[P_xxx]](无 |),不匹配 [[file_stem|P_xxx]] 或 [[P_xxx|display]]
WIKI_BARE_RE = re.compile(r"\[\[(P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)\]\]")

# 处理位置(派生层,raw 不动)
TARGET_DIRS = [
    "2_crystallized/themes",
    "2_crystallized/regions",
    "1_extracted/relations/_index_by_policy",
    "1_extracted/opinions",
    "1_extracted/entities",
]

# §6 graph 兜底段已经是 [[file_stem|P_xxx]] 格式,跳过
# 跳过文件:_summary.md / 索引页(它们用 alias 自洽)
SKIP_FILE_PATTERNS = ["_summary.md"]

stats = {"files_scanned": 0, "files_modified": 0, "links_converted": 0, "alias_unknown_skipped": 0}
modified_files = []


def convert(text, modified_count):
    def sub(m):
        pid = m.group(1)
        stem = pid_to_filestem.get(pid)
        if stem is None:
            stats["alias_unknown_skipped"] += 1
            return m.group(0)  # 留原样,B6 会标 dangling
        modified_count[0] += 1
        return f"[[{stem}|{pid}]]"
    return WIKI_BARE_RE.sub(sub, text)


for dir_rel in TARGET_DIRS:
    d = VAULT / dir_rel
    if not d.exists():
        continue
    for md in d.rglob("*.md"):
        if any(p in md.name for p in SKIP_FILE_PATTERNS):
            continue
        if "_archive" in md.parts:
            continue
        stats["files_scanned"] += 1
        text = md.read_text(encoding="utf-8", errors="ignore")
        cnt = [0]
        new_text = convert(text, cnt)
        if cnt[0] > 0:
            md.write_text(new_text, encoding="utf-8")
            stats["files_modified"] += 1
            stats["links_converted"] += cnt[0]
            modified_files.append((str(md.relative_to(VAULT)), cnt[0]))

print(f"\n=== B8 显式化报告 ===")
print(f"files_scanned: {stats['files_scanned']}")
print(f"files_modified: {stats['files_modified']}")
print(f"links_converted: {stats['links_converted']}")
print(f"alias_unknown_skipped: {stats['alias_unknown_skipped']} (这些是 dangling,B6 会处理)")
print(f"\nTop 10 modified:")
for f, n in sorted(modified_files, key=lambda x: -x[1])[:10]:
    print(f"  {f}: +{n} links")
