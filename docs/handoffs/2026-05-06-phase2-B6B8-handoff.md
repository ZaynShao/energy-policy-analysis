---
title: 2026-05-06 Phase 2 B6+B8 handoff — 新 session 接手
date: 2026-05-06
prev_commits:
  - 100e403 feat(B5)
  - 6d943ee feat(B2+B3)
  - e370cac feat(B1)
  - 8c7bbf3 fix(B0)
target: 新 session(auto mode)
priority: P0
estimated_time: 30-45 min(全 deterministic,无 LLM 调用)
---

# Handoff:B6 dangling pid 全景扫 + B8 派生层 wiki link 显式化

Phase 2 主任务 B0-B5 已完成(commits 8c7bbf3 / e370cac / 6d943ee / 100e403)。
本 handoff 给新 session 接手 P0 余量:**B6 + B8 一并做**(共用索引,姊妹任务)。

---

## 0. 用户已发现的 3 个问题(本会话末尾)

用户看 vault graph view 截图后报:

1. **Q1 — relations 中有 P_1900 假链接,日期 2027-01-01,文件不存在**
   → 性质:**dangling LLM 幻觉边**(可能在 jsonl from/to 或 evidence 中)+ 部分 fm.date
   异常(2027 未来日期,本会话 B3 没动 date)
   → 解决:**B6** dangling 全景扫 + cleanup

2. **Q2 — opinions-summary 中很多空链接政策,用户搜了大多真实存在**
   → 性质:**Obsidian alias 解析 bug**(不是 dangling,真有 raw 文件)
   → 解决:**B8** 把 §1-§5 内 [[P_xxx]] 全转 [[file_stem|P_xxx]] 显式格式
   (同 §6 graph 兜底段格式 — 一脉相承)

3. **Q3 — 关系图谱大量孤立**
   → 性质:**已知现状**(132 isolated,B2 trigger F 已审 118 候选,剩余真孤儿)
   → 解决:**B7**(P1,后做)分类打 tag

本会话已答复用户 Q1-Q3 真因,B6+B8 是 P0 紧迫项。

---

## 1. 工作目录 + baseline

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# 验证起点(应见这 4 个 commit)
git log --oneline -6
# 100e403 feat(B5): opinions-summary 13 主题重生
# 6d943ee feat(B2+B3): trigger F 全候选 35 边 + issuer/region 78 篇 LLM 修复
# df328b2 feat(topic_distribution): 直辖市下辖区...(其他 session 提交)
# e370cac feat(B1): entities 全量重抽 + 13 主题 crystallize
# 8c7bbf3 fix(B0 alias regex)
# 62c3c84 feat(audit_2026-05-06)

# 当前 metric
python3 _meta/scripts/relations_coverage_metric.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['summary'])"
# 应见 policies=664 / total_edges=1148 / isolated=132 / bidirectional=150

# 当前履历
wc -l _meta/audit/{rel_judge,stance,opinions_summary}_history.jsonl
# 781 / 189 / 22

# alias collision 应是 0
python3 -c "from pathlib import Path; import re; pat=re.compile(r'^P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*\$'); c=[p for p in Path('.').rglob('*.md') if '.git' not in p.parts and '_archive' not in p.parts and pat.match(p.stem)]; print(f'collision: {len(c)}')"
```

---

## 2. 共用索引(B6 + B8 都要建)

写 `_meta/scripts/oneshot_build_pid_filestem_index.py`:

```python
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
```

跑一次:
```bash
python3 _meta/scripts/oneshot_build_pid_filestem_index.py
# 预期:vault_pids 664 / pid_to_filestem 664
```

---

## 3. B6 — dangling pid 全景扫 + cleanup

### 3.1 扫描脚本 `_meta/scripts/oneshot_scan_dangling_pids.py`

扫 4 类位置,产 audit 报告:

```python
"""扫 vault 全部 dangling pid 引用,产 audit 报告"""
from pathlib import Path
import re, json, yaml
from datetime import datetime

VAULT = Path(__file__).resolve().parent.parent.parent
PIDS_FILE = VAULT / "_meta" / "audit" / "vault_pids.txt"

vault_pids = set(PIDS_FILE.read_text(encoding="utf-8").split())

PID_RE = re.compile(r"P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*")
WIKI_RE = re.compile(r"\[\[(P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)(?:\|[^\]]*)?\]\]")

report = {"scan_at": datetime.now().isoformat(), "categories": {}}

# (a) 1_extracted/relations/*.jsonl from/to dangling
cat = {"dangling_in_jsonl_field": []}
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
                cat["dangling_in_jsonl_field"].append({"file": jf.name, "line": ln_no, "field": k, "pid": v})
report["categories"]["dangling_jsonl_from_to"] = cat

# (b) 派生层 .md 中的 [[P_xxx]] wiki link 是否都对应 vault
cat = {"dangling_wiki_in_derivative_md": []}
for md in VAULT.rglob("*.md"):
    if any(part in md.parts for part in (".git", "_archive", "0_raw")):
        continue
    text = md.read_text(encoding="utf-8", errors="ignore")
    for m in WIKI_RE.finditer(text):
        pid = m.group(1)
        if pid not in vault_pids:
            cat["dangling_wiki_in_derivative_md"].append({"file": str(md.relative_to(VAULT)), "pid": pid})
report["categories"]["dangling_wiki_in_md"] = cat

# (c) raw 政策 fm.date 异常(未来日期 / 1900 与抓取日不一致)
cat = {"future_date": [], "year_1900_with_recent_fetch": []}
NOW_YEAR = datetime.now().year
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)
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
    # 未来日期
    m2 = re.match(r"(\d{4})", date)
    if m2 and int(m2.group(1)) > NOW_YEAR:
        cat["future_date"].append({"pid": pid, "date": date, "filename": p.name})
    # 1900 placeholder + 较新 fetch_at(说明真实日期是 fetch 那天)
    if date.startswith("1900") and "2026" in fetched:
        cat["year_1900_with_recent_fetch"].append({"pid": pid, "fetched_at": fetched, "filename": p.name})
report["categories"]["raw_fm_date_anomaly"] = cat

# (d) summary 输出
print(f"\n=== dangling 全景扫报告 ===")
print(f"vault 真实 pid: {len(vault_pids)}")
print(f"\n(a) jsonl from/to dangling: {len(report['categories']['dangling_jsonl_from_to']['dangling_in_jsonl_field'])}")
print(f"(b) 派生 .md wiki link dangling: {len(report['categories']['dangling_wiki_in_md']['dangling_wiki_in_derivative_md'])}")
print(f"(c) fm.date 未来日期: {len(report['categories']['raw_fm_date_anomaly']['future_date'])}")
print(f"(c) fm.date=1900 + recent fetch: {len(report['categories']['raw_fm_date_anomaly']['year_1900_with_recent_fetch'])}")

out = VAULT / "_meta" / "audit" / "dangling_scan_2026-05-06.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告写到 {out}")
```

跑:
```bash
python3 _meta/scripts/oneshot_build_pid_filestem_index.py
python3 _meta/scripts/oneshot_scan_dangling_pids.py
```

预期发现:
- (a) jsonl dangling 应该 ~0(apply 都有 dangling 校验)— 如果有就是历史漏校验,需要 cleanup
- (b) 派生 .md wiki link dangling 可能 100+ — 多数是 LLM 在 opinions-summary §1-§4 evidence/reason 引用了 vault 外 pid,或 5C derives_from 链
- (c) future_date 应该几个 — 修 fm.date,走 SKILL §6 协议(备份 + audit 字段)
- (c) 1900+recent_fetch 可能几十个 — 这些是抓取时 date fallback bug,需要 LLM 重抽真实政策日期(派 1 subagent)

### 3.2 cleanup 脚本 `_meta/scripts/oneshot_cleanup_dangling.py`

针对扫到的 dangling:
- (a) jsonl from/to dangling → backup jsonl 到 `1_extracted/_archive/relations/`,
  从 jsonl 删该行(罕见,如果有的话)
- (b) 派生 .md wiki link dangling → 改为 `[[~~P_xxx~~ (dangling)]]` 删除线 +
  注释,或直接删整段引用(看具体 case)
- (c) future_date → 走 SKILL §6 协议:备份 raw + 改 fm.date + 加
  `provenance.date_fixed_at / date_fixed_method / date_fixed_from`
- (c) 1900+recent_fetch → 派 1 subagent 读 body 头 1500 字抽真实日期,再走
  §6 协议改

具体实现按上述 B3 issuer 修复脚本(`oneshot_apply_issuer_region_fix.py`)的
模板复用,关键:**用 line-anchored regex `^---\s*\n(.*?)\n---\s*(\n|$)` 找 fm 边界**
(本会话踩过的坑:naive `find('---', 3)` 在 title 含 `---` 时会截短,P_1900_GO_e6f6f834
/ P_2024_GO_dfcfe98b 受影响,已修复脚本。新脚本沿用同样 regex)。

---

## 4. B8 — 派生层 wiki link 显式化

### 4.1 修复目标

opinions-summary §1-§5(以及 timeline.md / regional-coverage.md / _global_index.md
等所有派生 .md)中的 `[[P_xxx]]` 形式 → 转为 `[[file_stem|P_xxx]]` 显式格式。
原则:Obsidian 文件名优先 > alias,显式 link 100% 可点,不依赖 alias 索引。

### 4.2 脚本 `_meta/scripts/oneshot_explicit_wiki_links.py`

```python
"""把派生层 .md 中的 [[P_xxx]] 转为 [[file_stem|P_xxx]] 显式格式"""
from pathlib import Path
import re, json

VAULT = Path(__file__).resolve().parent.parent.parent
MAP_FILE = VAULT / "_meta" / "audit" / "pid_to_filestem.json"

pid_to_filestem = json.loads(MAP_FILE.read_text(encoding="utf-8"))

# 匹配 [[P_xxx]](无 |),不匹配 [[file_stem|P_xxx]] 或 [[P_xxx|display]]
# 严格 alias 模式
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
```

### 4.3 跑 + 验证

```bash
# 1. 跑显式化
python3 _meta/scripts/oneshot_explicit_wiki_links.py
# 预期:files_modified ~50-100,links_converted ~1500-3000

# 2. 验证 — 同 B5 末尾的检测
python3 << 'EOF'
import re
from pathlib import Path
NAKED = re.compile(r'(?<![\[\|])P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*')
total_naked = 0
for p in Path('2_crystallized/themes').glob('*/opinions-summary.md'):
    text = p.read_text(encoding='utf-8')
    end = text.find('---', 3)
    body = text[end+3:] if end > 0 else text
    s6 = body.find('# 关联政策清单')
    before_s6 = body[:s6] if s6 > 0 else body
    n = len(NAKED.findall(before_s6))
    total_naked += n
print(f'§1-§5 裸 pid: {total_naked}')  # 应仍是 0

# 验证 [[P_xxx]] alias 形式 vs [[file_stem|P_xxx]] 显式形式
ALIAS = re.compile(r'\[\[(P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)\]\]')
EXPLICIT = re.compile(r'\[\[[^\[\]]+?\|(P_\d{4}_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)\]\]')
total_alias = total_explicit = 0
for p in Path('2_crystallized').rglob('*.md'):
    text = p.read_text(encoding='utf-8', errors='ignore')
    total_alias += len(ALIAS.findall(text))
    total_explicit += len(EXPLICIT.findall(text))
print(f'2_crystallized alias [[P_xxx]]: {total_alias}')  # 应大幅下降
print(f'2_crystallized explicit [[stem|P_xxx]]: {total_explicit}')  # 应大幅上升
EOF
```

---

## 5. commit 策略

跑完 B6 + B8 后两个独立 commit:

```bash
# B6 commit
git add _meta/scripts/oneshot_build_pid_filestem_index.py \
        _meta/scripts/oneshot_scan_dangling_pids.py \
        _meta/scripts/oneshot_cleanup_dangling.py \
        _meta/audit/vault_pids.txt \
        _meta/audit/pid_to_filestem.json \
        _meta/audit/dangling_scan_2026-05-06.json \
        0_raw/policies/ \
        0_raw/_archive/policies/ \
        1_extracted/  # cleanup 改的 jsonl + 派生 md

git commit -m "feat(B6): dangling pid 全景扫 + cleanup..."

# B8 commit
git add _meta/scripts/oneshot_explicit_wiki_links.py \
        2_crystallized/ \
        1_extracted/relations/_index_by_policy/ \
        1_extracted/opinions/ \
        1_extracted/entities/

git commit -m "feat(B8): 派生层 wiki link 显式化 — Obsidian alias 解析失败兜底"
```

---

## 6. 完成验收

跑完后给用户报告:

1. **5 类指标 before/after**:
   - vault_pids 数(应 = 664)
   - dangling 4 类各多少(jsonl from/to / 派生 md wiki / future_date / 1900_with_recent_fetch)
   - 显式化 links_converted 数 / files_modified 数
   - alias collision 仍是 0
   - opinions-summary §1-§5 裸 pid 仍是 0

2. **commits 列表**:2 个新 commit hash

3. **用户验证步骤**:
   - 在 Obsidian 里再次打开任意 opinions-summary.md
   - 点 §1/§2/§3 中任意 [[P_xxx]] → 应能跳转到 raw 政策
   - 看 graph view → dangling 节点应显著减少

---

## 7. 已知坑 / 注意

1. **fm 边界 regex 必须 line-anchored**(本会话踩过):
   ```python
   FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(\n|$)", re.DOTALL)
   ```
   不要用 `text.find('---', 3)` — title 含 `---` 时会截短(2 个真实案例:
   P_1900_GO_e6f6f834 / P_2024_GO_dfcfe98b)。

2. **修 raw fm.date 走 SKILL §6 协议**(P0):备份 + audit 字段
   - 备份到 `0_raw/_archive/policies/{filename}__pre_date_fix_<ts>.md`
   - 加 provenance.date_fixed_at / date_fixed_method / date_fixed_from
   - body 完全不动

3. **§6 graph 兜底段已经是 [[file_stem|P_xxx]] 格式**,B8 脚本应跳过它(WIKI_BARE_RE
   只匹配无 | 的 [[P_xxx]])。

4. **`_summary.md` 文件可能用 alias 自洽**(它们是聚合索引页,引用规则不同),
   保守起见 SKIP 列表里加 `_summary.md` pattern。

5. **派生 _rev_*.md / _op_*.md 文件本身命名带前缀**(522bc99 引入),里面的
   [[P_xxx]] 同样需要显式化 — 它们在 `1_extracted/relations/_index_by_policy/`
   和 `1_extracted/opinions/` 已列入 TARGET_DIRS。

6. **B6 cleanup 中不要直接删 jsonl 行 — 先 backup 整文件到 `1_extracted/_archive/relations/{filename}__pre_dangling_cleanup_<ts>.jsonl`**,
   然后写新文件(过滤掉 dangling 行)。SKILL §6 同样适用关系层。

7. **跑 B6 + B8 之后必须重跑 deterministic post-llm**:
   ```bash
   python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
   ```
   理由:cleanup 改了 jsonl,需要刷新 reverse_links + global_index。

---

## 8. 时间预算

- B6 索引 + 扫描:5 min(全 deterministic)
- B6 cleanup(jsonl + future_date):10 min
- B6 1900+recent_fetch 派 subagent(可选,如果数量 >20):15 min
- B8 显式化 + 验证:5 min
- deterministic post-llm:5 min
- 2 个 commit + 总报告:5 min

**总计 35-50 min**(看 1900+recent_fetch 是否需要 subagent)。

---

## 9. 一句话总结

> B6 扫 vault 全部 dangling pid(jsonl 字段 + 派生 md wiki link + raw fm.date
> 异常)+ cleanup;B8 把派生层所有 `[[P_xxx]]` alias 转为 `[[file_stem|P_xxx]]`
> 显式格式,与 §6 graph 兜底段同格式。两项共用 vault_pids + pid_to_filestem 索引,
> 一次会话 30-50 min 全 deterministic 收工。完成后用户在 Obsidian 里点
> opinions-summary 的链接 100% 可跳。
