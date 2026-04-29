# Handoff · 链接体系优化 follow-up session

**交接日期**:2026-04-29 17:00
**交接方**:链接体系返工 session(commit `258997a`)
**接收方**:链接优化 follow-up session(本文档读者)
**前置阅读时间**:5-10 分钟

---

## 0. 一句话总结

上一轮把 vault 的链接体系做了重量级返工(评论关联 11%→24%、反链页 71→189 双向化、263 政策加 aliases、dup 隔离)。**这一轮你要做的是 follow-up 5 个 G 系列任务**,把"已识别但没来得及做"的事收尾,然后回答"是否启动 L3 月报 dryrun"。

---

## 1. 你的任务范围

**核心 5 个 follow-up(用户让你挑做)**:

| # | 任务 | 耗时 | 价值 |
|---|------|------|------|
| **G1** | 补采 vault 缺的 8 条核心政策 | 1-2h | ⭐⭐⭐⭐⭐ |
| **G2** | 7 条老政策漏抓的关系补抽 | 30 min | ⭐⭐⭐⭐ |
| **G3** | 修反链页 commentary section 引入的 60 条 dangling | 30 min | ⭐⭐ |
| **G4** | B2 标题模糊匹配 130 条人工抽查 | 30 min | ⭐⭐⭐ |
| **G5** | 评论价值分类(剔除化工/法律类,标 `not_policy_related`)| 1h | ⭐⭐⭐⭐ |

**不在你范围**:
- L3 月报实战(单独 session,看 `2026-04-28-l3-monthly-report-handoff.md`)
- L2 opinion 重抽(990 篇 A 类)
- conflicts schema 转型
- L1 采集层升级

**如果 5 个 G 全做完**,返回给用户讨论:启动 L3 月报 dryrun? 还是去补 L2 opinion?

---

## 2. 上一轮做了什么(commit `258997a`,610 文件)

**9 项任务全部完成**:

| 项 | 动作 |
|---|---|
| D1 | `_duplicates/` 加 Obsidian `userIgnoreFilters` |
| D2 | 3 个真 dup 标 frontmatter `_duplicate_of` + 1 条误判从归档恢复到 iterates |
| CLAR | schema_v3 加 §6.5(4 象限覆盖率口径)+ §6.6(双向反链规范)|
| B1 | 评论文号严格匹配 → +14 条 |
| B2 | 评论标题模糊匹配 → +130 条 |
| B3 | 4 路 LLM subagent 精判 890 评论 → +6 条高置信 |
| X1+B4 | 反链页 V2:双向(入向+出向)+ commented_by section,71→189 页 |
| X2 | 24 老孤立政策诊断,7 条关系网真漏抓已识别 |
| Aliases | 263 政策 frontmatter 加 `aliases: [P_xxx]`(Obsidian wiki 解析)|

**vault 状态变化**:
- 反链页面: 71 → **189**
- 评论关联率: 11.2% → **24.0%**(131 → 281)
- dangling 链接: 371 → **166**(-55%)
- typed relations 总边: 447 → 373(归档/收紧后)
- aligns_with: 112 → 38(阈值 0.78)
- iterates: 26 → 23
- clarifies: 69 → 73

---

## 3. 5 个 G 任务的具体落地点

### G1 · 补采 8 条核心政策(L1 collection)

LLM 判定时反复提到"政策但不在 catalog",这些是 L1 采集缺口:

| 政策 | 重要性 |
|---|---|
| **国家发改 650 号文** 绿电直连(2025) | 多省细则都引用 |
| **国家发改 114 号文** 容量电价新规(2026) | 储能资产化关键文件 |
| **生态环境法典** | 跨行业基础法 |
| 福建省调计 2026 29 号(辅助服务管理) | 评论高频引用 |
| 湖南分时电价湘发改价调规 2025 385 号 | 评论高频 |
| 陕西电力市场细则系列 | 评论高频 |
| 四川省 14-5 规划纲要(2026-04-13)| 评论高频 |
| 国务院关于产业链供应链安全的规定 | IIGF 解读 |

**做法**:
- 走 L1 采集 SOP:`00 背景资料/L1-政策采集SOP.md`
- 用 tavily + trafilatura 抓 → 0_raw/policies/
- 跑 L2 抽取(关系/实体/diff)

### G2 · 7 条老政策漏抓的关系补抽

```
P_2015_GO_73         充电基建国办 73 号 (2015)    ← 应被 P_2023_GO_19_b supersedes
P_2017_NDRC_09206e37 电力需求侧管理(2017)        ← 应被 2023 版迭代
P_2018_NDRC_364      电力系统调节能力指导(2018)   ← 应被多条 cites_basis
P_2022_NDRC_032146fe 14-5 新型储能方案 (2022)    ← 应被 P_2024_NDRC_0806117c iterates
P_2023_NDRC_178      节能降碳重点设备更新 (2023) ← 应被 P_2024_SC_7 cites_basis
P_2023_NDRC_1294_b   电力系统稳定指导 (2023)     ← 应被 P_2025_NDRC_1656_a supersedes
P_2023_NDRC_0915531d 电力负荷管理 2023            ← 应被 VPP 政策 references
```

**做法**:
- 直接 LLM 一次判定 7 条 + 候选政策
- 写到对应 jsonl(supersedes/iterates/cites_basis/references)
- 重跑反链页:`python3 /tmp/rebuild_reverse_links_v2.py`(脚本还在 /tmp)

### G3 · 修反链页 commentary 区 dangling

反链页 V2 在 commentary section 用 `[[评论文件 stem]]`,但少数评论文件名含全角标点(",":《》等)解析失败,引入 60 条新 dangling。

**做法**:
- 扫 `_index_by_policy/*.md` 找 `[[]]` 链接
- 对每条解析失败的 stem,看是否有匹配文件(模糊)
- 修正 `rebuild_reverse_links_v2.py` 用 markdown link `[text](path)` 替代 wiki link
- 或者:把 commentary 文件名加 `aliases` 字段(类似政策 aliases 方案)

### G4 · B2 标题模糊匹配 130 条人工抽查

B2 用了 8-gram 标题匹配,精度估计 70-80%。可疑案例:
- "AI算力爆发,数据中心电力供给迎大考" → P_2026_NPC_03132f88(可能误判)
- "8GW+出货背后,构网型储能..." → P_2024_NM_0101e295(可能误判)

**做法**:
- 找所有 `related_policy_source: B2_title_fuzzy` 的评论
- 抽 30 条人工核
- 错误率 > 30% → 全量回滚 B2 重做(更严格的策略,如要求文号同时匹配)
- 错误率 < 15% → 保留

### G5 · 评论价值分类

B3 揭示:1170 评论里 ~70% 是化工/法律/AI/海外新闻,**没有政策可关联**。

**做法**:
- frontmatter 加字段 `not_policy_related: true`(根据规则筛选)
- 规则提议:
  - business_tag=power AND title 含化工词(硫磺/磷酸/电石/纯碱/PVC...)→ true
  - title 含法律词(破产/诉讼/欧盟/UFLPA/ESG)→ true
  - source_account 是新闻汇总类(绿色金融日报/中能财经/IIGF...)→ 部分 true
- 这样真实关联率公式变为 `linked / (total - not_policy_related)`,会跳到 80%+

---

## 4. 关键文件/脚本位置

### vault 根
`/Users/shaoziyuan/Documents/Zayn Main/`(Obsidian vault)
- `.obsidian/app.json` — `userIgnoreFilters` 已配置 staging + _duplicates

### 政策分析项目根(git repo)
`/Users/shaoziyuan/Documents/Zayn Main/政策分析/`

```
0_raw/
  policies/        263 政策(全部已加 aliases)
  commentaries/   1170 评论(281 已 related_policy)
  _duplicates/     71 (Obsidian 隔离)
1_extracted/
  relations/
    *.jsonl        7 类关系
    _index_by_policy/ 189 反链页(双向 + commented_by)
    _archive_aligns_v3_below_0.78.jsonl(70 条裁剪)
    _archive_aligns_v3_migrated_to_clarifies.jsonl(4 条)
    _archive_iterates_dedup_v3.jsonl(3 条)
2_crystallized/
  themes/   32 主题结晶页
  regions/   9
_meta/
  schema_v3.md  ← §6.5/§6.6 已更新
  scripts/      L1/L2 工具
```

### /tmp 临时脚本(可复用)
- `/tmp/rebuild_reverse_links_v2.py` — 反链页双向重建,改完 jsonl 直接跑
- `/tmp/b1_match_official_number.py`
- `/tmp/b2_match_title.py`
- `/tmp/b3_merge.py` — 合并 4 chunks B3 结果
- `/tmp/add_aliases.py` — 政策 aliases 补丁(已跑过,不需重跑)
- `/tmp/d2_handle_dups.py` — dup 处理
- `/tmp/eval_v3_*.py` — 关系网评估脚本

### 备份(可恢复)
- `/tmp/iterates.jsonl.bak` / `/tmp/aligns_with.jsonl.bak` / `/tmp/clarifies.jsonl.bak`
- `/tmp/_index_by_policy.bak/` — 旧反链页 71 个

---

## 5. 用户偏好/约束(必读)

来自 `~/.claude/projects/-Users-shaoziyuan-code/memory/`:

1. **滴滴能源政策分析项目**,Obsidian + OpenClaw 工作流
2. **当前在中国**,需走代理访问 Claude/外网
3. **开发日记格式**:`开发日记/<YYYY-MM-DD>/日志.md`
4. **问方向时列大框架 todo**:A/B/C 选项前先列全局 TODO,标出推进/解锁/不触哪几条
5. **用户语言**:中文为主(技术词英文)
6. **行为规则**:CLAUDE.md 强调 "Think Before Coding" / "Simplicity First" / "Surgical Changes" / "Goal-Driven Execution"

---

## 6. 已知陷阱

1. **vault 文件名是中文带【】**,不是 P_xxx.md。Obsidian 用 `aliases` 解析 `[[P_xxx]]` 到正确文件。所有政策已加 aliases。

2. **subagent 沙箱限制**:不能直接读 vault,不能写 /tmp/。让 subagent 把 JSONL 输出在 final_report markdown code block 里,主 session 提取保存。

3. **iterates 4 条 dup 已经处理**(3 归档,1 恢复),不要再当作"漏抓"重新抽。

4. **aligns_with 阈值已收紧到 0.78**,不要往下放(0.70-0.77 区间错判率高)。

5. **政策 ID 后缀 `_a/_b/_c` 不是 dup**!是同年同号但不同部门发文(沪商市场〔2025〕21 vs 沪发改环资〔2025〕21)。**不要尝试合并**。

6. **commentary 关联率 24% 已接近上限**,真正可关联的政策评论可能只有 30-40%(剩下都是行情/法律/产品发布)。要再提升必须先做 G5(价值分类)。

7. **git repo 根在 政策分析/ 子目录**,不在 vault 根。`.obsidian/app.json` 不在 git 里(用户 vault 配置)。

---

## 7. 启动顺序建议

```
第 1 步 (5 min) - 同步上下文
  - 读 README.md(项目总览)
  - 读 _global_index.md(数据全貌)
  - 看 git log -10(最近 commit 风格)
  - 看 commit 258997a 详情

第 2 步 (5 min) - 让用户选先做哪几个 G
  - 列 G1-G5 表 + 推荐 G1+G2(高价值)
  - 等用户选

第 3 步 - 执行 + 中间验证
  - 每做一个 G,跑一次反链页重生 + dangling 扫描
  - 单独 commit 每个 G(便于回滚)

第 4 步 (收尾) - 让用户选后续大方向
  - L3 月报 dryrun?
  - L2 opinion 重抽?
  - L1 补采更多?
```

---

## 8. 验证脚本(粘进 bash 跑)

```bash
# 当前数据状态
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"
echo "=== relation jsonl ===" && wc -l 1_extracted/relations/*.jsonl
echo "=== reverse-link pages ===" && ls 1_extracted/relations/_index_by_policy/ | wc -l
echo "=== policies ===" && ls 0_raw/policies/ | wc -l
echo "=== commentaries ===" && ls 0_raw/commentaries/ | wc -l

# 评论关联率
python3 -c "
import re, yaml
from pathlib import Path
FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
total, linked = 0, 0
for f in Path('0_raw/commentaries').glob('*.md'):
    total += 1
    text = f.read_text(errors='ignore')
    m = FM_RE.match(text)
    if not m: continue
    fm = yaml.safe_load(m.group(1)) or {}
    rp = fm.get('related_policy')
    if rp and rp not in ['', None, [], '~']:
        linked += 1
print(f'commentary 关联率: {linked}/{total} = {linked/total*100:.1f}%')
"

# 当前 dangling(Obsidian 视角)
cd "/Users/shaoziyuan/Documents/Zayn Main"
python3 -c "
import re, yaml
from pathlib import Path
all_mds = [p for p in Path('.').rglob('*.md')
           if not any(x in p.parts for x in ['.archive','.obsidian','.git','staging','_duplicates'])]
name_to_path = {}
FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
for p in all_mds:
    name_to_path.setdefault(p.stem, []).append(p)
    text = p.read_text(errors='ignore')
    m = FM_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
            for a in (fm.get('aliases') or []):
                name_to_path.setdefault(str(a), []).append(p)
        except: pass
wiki_re = re.compile(r'\[\[([^\]|#]+)(?:#[^\]]+)?(?:\|[^\]]+)?\]\]')
total, dangling = 0, 0
for p in all_mds:
    for m in wiki_re.findall(p.read_text(errors='ignore')):
        total += 1
        if m.strip().split('/')[-1] not in name_to_path:
            dangling += 1
print(f'wiki link: {total}, dangling: {dangling}')
"
```

---

## 9. 一句话目标

**用 1-3 小时把 G1-G5 做掉(或挑 2-3 个高价值的),让链接体系不再有"已知漏点"**,然后把决策权交还给用户:启动 L3 月报 dryrun,还是去做 L2 opinion 重抽?

祝好。

— 上一轮 session(2026-04-29 commit `258997a`)
