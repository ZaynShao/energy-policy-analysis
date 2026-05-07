---
name: policy-vault-l2-rebuild
description: 在「政策分析」vault(0_raw/policies + 0_raw/commentaries 路径下)做了 L1 改动(新政策入库/raw body 重抓/评论 frontmatter 改/关系修正/dedup)后,触发 L2 派生 + L3 结晶的全链路重建,杜绝漏跑 opinions/关系/反链/主题/business_view 等任何下游层。任何时候用户在此 vault 提到"加新政策""重抓政策""评论审阅""5C 派生""business_view yaml""反链 stale""主题 stale""opinions 失效""我刚改了 raw"——即使没说 rebuild——都必须使用此 skill。本 skill 避免了过去发现的 staleness 黑洞:opinions-summary/W1+W2 关系层/L3 重要性 bug。
---

# Policy Vault L2 Rebuild

服务于 `/Users/shaoziyuan/Documents/Zayn Main/政策分析/` vault(滴滴能源政策分析项目)。**L1 raw 一旦改动,L2/L3 派生层会出现 staleness**,本 skill 教会你识别 trigger 类型 + 跑 `_meta/scripts/rebuild_l2.py` 编排器完成全链路重建。

---

## 0. 触发判定(立即决定 trigger 类型)

读完用户当前请求,立即归类到 1 种 trigger:

| 用户做了什么 | trigger | 信号词 |
|---|---|---|
| 新政策入库(write 到 `0_raw/policies/`) | **A. pid_change** | "采集 X 政策"、"L1.3 W3"、"加 N 篇政策"、新 P_xxx 出现 |
| 现有 raw body 重抓(替换 body,frontmatter 不动) | **A. pid_change** | "重抓 PDF"、"OCR 重做"、"body 替换" |
| 评论 frontmatter 改(`related_policy` / `not_policy_related` 字段变) | **B. commentary_change** | "评论审阅"、"P4 重判"、"重新链接评论"、"批量标 not_policy_related" |
| 关系层手动加边(supersedes 等) | **C. 仅跑 deterministic post-llm** | "20 号令 supersedes 15 号令"、"加 cites_basis" |
| L1 dedup / 文件名改(pid 不变) | **C. 仅跑 deterministic post-llm** | "dedup"、"文件名规范化" |
| 全量校验或 deterministic 全跑 | **D. deterministic --scope all** | "全部重跑一遍"、"audit"、"vault 体检" |
| 上位政策反向 inbound 边补全 | **E. reverse_cites** | "P_xxx inbound 偏低"、"反向 cites_basis"、"上位政策反向边" |
| 关系层 isolated 政策一次清账(已入库政策重审) | **F. rel_judge_rerun** | "isolated 政策"、"重审已入库 rel_judge"、"召回率 audit"、"P_xxx outbound 0" |

**关键判定**:看用户是否动了 `0_raw/`。raw 没动只是 deterministic 重跑的(C/D)不需要 LLM subagent。
**reverse_cites 与 trigger A 不同**:不动 raw,只对已有 vault 政策派 LLM judge 找未抽到的反向 cites_basis 边(基于关系层覆盖率 metric 诊断的缺口)。
**rel_judge_rerun 与 reverse_cites / trigger A 不同**:对**已入库 isolated 政策**(metric 报双 0)从 outbound 视角重跑 5 类关系 LLM judge。不动 raw,不动 5C(business_view yaml 不重写),纯关系层重审。判别 isolated 政策是真孤儿还是召回不足。

---

## 1. 通用工作流框架

任何 trigger 都按 4 阶段:

```
trigger → prepare(stage) → 派 subagent → apply → deterministic post-llm
            ↑                    ↑           ↑              ↑
       脚本自动             用户手动      脚本自动         脚本自动
```

主编排脚本: **`_meta/scripts/rebuild_l2.py`**(已实现,见 `--help`)

LLM 任务的 staging 状态目录: **`_l2_rebuild_state/`**(在 cwd 下,本地 only,已在 .gitignore)

---

## 2. Trigger A: pid_change(新政策 / body 重抓)

完整 5 步,**前置 audit 闸**(2026-05-06 加入)在 prepare 内自动跑:

### A.1 准备阶段(`prepare`)

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids P_xxx,P_yyy,P_zzz
```

脚本自动 4 步(失败任一步即阻断):
- **step 0 前置 audit**(LLM Wiki §1 数据合规闸,2026-05-06 加入):
  - `validate_l1.py --pid X,Y` — fm 必填 / enum / ISO ts
  - `oneshot_l1_body_audit.py --pid X,Y` — PDF binary / HTML residue / title-body recall
  - `oneshot_l12_residue_audit.py --pid X,Y` — fm 违规 LLM 派生字段 / body 派生 section
  - 任一 error/suspicious/violation → **阻断**;按建议修 raw 后重跑(强制跳过设 `SKIP_PREFLIGHT_AUDIT=1`)
- step 1 deterministic 前置:`extract_relations_regex.py --references-only` + `extract_entities.py`
- step 2 stage `_l2_rebuild_state/5c/{inputs.jsonl, prompt.md}`(5C 派生 LLM 任务)
- step 3 stage `_l2_rebuild_state/rel_judge/{inputs.jsonl, vault_index.jsonl, prompt.md}`(关系 LLM judge)

### A.2 派 2 个 subagent(opus 4.7,可并行后台)

读 `_l2_rebuild_state/5c/prompt.md` 和 `_l2_rebuild_state/rel_judge/prompt.md` 各派 1 subagent(`run_in_background: true`)。subagent 的 results 必须写到:
- `_l2_rebuild_state/5c/results/results.jsonl`
- `_l2_rebuild_state/rel_judge/results/results.jsonl`

提示词模板已经在 prompt.md 里完整写好,不需要再加工 — 直接 copy 给 subagent 即可。如需调整决策规则,见 `references/subagent-prompts.md`。

### A.3 应用 LLM 结果(2 个 apply)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
```

`apply --stage 5c` 内部走 `oneshot_apply_5c_subagent_results.py`,写 3 处:
- `_meta/business_view/{pid}.yaml`
- `1_extracted/policy_summaries.jsonl`(upsert)
- `1_extracted/relations/derives_from.jsonl`(replace by from)

`apply --stage rel` 把 5 类关系增量写到 `1_extracted/relations/{cites_basis,iterates,extends,clarifies,aligns_with}.jsonl`(防重 by `(from, to)`)。

**B 阶段强校验**(2026-05-06 加入):
- `apply --stage 5c` 在跑 oneshot_apply 前先校验 results.jsonl schema —
  pid / summary(≥10 字)/ scores 6 维(D1-D6 ∈ [0,5])/ 影响分析 4 段(加油 / 充电 /
  电力_储能_V2G_交易 / 乡村)— 任一缺即阻断,要求 LLM 重跑生成完整 schema
- `apply --stage rel` 用 `_load_vault_pid_set()` 校验 from/to 必须真存在 vault —
  dangling pid(LLM 偶发幻觉一个不存在的 pid)直接 skip + 警告,不写入 jsonl
- `apply --stage rev_cites` 同样跑 dangling 校验

### A.4 跑 post-LLM deterministic

```bash
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

链:`crystallize_theme.py --all`(9 主题刷新 _input.json + timeline + regional-coverage)→ `build_regions.py` → `build_global_index.py` → `build_reverse_links.py`

### A.5 验证 + commit

```bash
git status --short | head -20
# 应看到:0_raw/policies/<新加的>.md(新增)、_meta/business_view/<新加的>.yaml(新增)、
#   1_extracted/relations/*.jsonl(增量)、2_crystallized/(刷新)、_index_by_policy/(同步)
git add ... && git commit -m "..."
```

**特例 — body 重抓**(如 14 PDF 乱码案):多一个前置步骤,见 `references/body-refetch-pattern.md`。核心:`0_raw/_archive/policies/` 备份 + `provenance.body_refetched_at` audit 字段。

---

## 3. Trigger B: commentary_change(评论 frontmatter 改)

完整 5 步(双 LLM 阶段):

### B.1 准备阶段(stance)

```bash
# 全量重抽 191 linked
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --all-commentaries

# 或只重抽指定评论
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --commentaries X.md,Y.md
```

stage 4 batches `_l2_rebuild_state/stance/batch_{1..4}.jsonl` + `prompt.md`。

### B.2 派 4 个 subagent(stance,可并行)

读 `_l2_rebuild_state/stance/prompt.md`,派 4 subagent 各跑 1 batch,results 写 `_l2_rebuild_state/stance/results/batch_{1..4}.jsonl`。

### B.3 apply --stage stance(自动级联)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage stance
```

内部:
- 备份现有 stance_batches → `_pre_rebuild_l2_backup/`
- 4 batch 合并 → 5 等份切回 `agent_{1..5}_stances.jsonl`
- 跑 `aggregate_opinions.py` → `1_extracted/opinions/<pid>.md` 重写
- 清理 stale opinion .md(>60s 未更新)
- 跑 `crystallize_theme.py --all` 刷新 9 主题 _input.json(opinion_pids 新值)
- **自动 stage opinions-summary 第 2 LLM 阶段** → `_l2_rebuild_state/opinions_summary/spec_{1..3}.json`

### B.4 派 3 个 subagent(opinions-summary,可并行)

读 `_l2_rebuild_state/opinions_summary/prompt.md`,派 3 subagent 各 1 spec(每 spec 含 3 主题)。subagent **直接 Write 到 vault 路径** `2_crystallized/themes/<theme_dir_name>/opinions-summary.md`(2_crystallized 是 L3 派生层,允许写)。

### B.5 apply --stage opinions-summary

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage opinions-summary
```

校验 9 个 opinions-summary.md 都 fresh + 跑 `build_reverse_links.py` 同步。

---

## 4. Trigger C: 关系层手动加 / dedup(无 LLM)

不需要 prepare/apply,直接 deterministic:

```bash
# 加边到 jsonl 后(如手动加 supersedes)
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

或全量:

```bash
python3 _meta/scripts/rebuild_l2.py deterministic --scope all
# = references + entities + 9 主题 crystallize + regions + global_index + reverse_links
```

---

## 4b. Trigger E: reverse_cites(2026-05-06 加入,T4 反向上位 inbound 补全)

诊断:跑 `relations_coverage_metric.py` 看上位政策 inbound 是否偏低/为 0。如果是,这 trigger 用 LLM judge 找 vault 内未抽到的反向 cites_basis 边。

完整 3 步:

### E.1 准备(`prepare`)

```bash
python3 _meta/scripts/rebuild_l2.py prepare --trigger reverse_cites \
  --target-pids P_2024_GO_L775,P_2018_NDRC_364,P_2024_NDRC_20
```

脚本自动:
- 加载 vault 全 271 政策 body
- 对每 target,**预过滤候选**(2 轨):
  - hard hit: target official_number 核心 token(`〔YYYY〕XX号` / `第N号`)精确出现在 candidate body
  - soft hit: candidate body 前 3000 字含 ≥3 个 target.title jieba 关键词,且至少 1 个 ≥ 4 字核心词
- stage `_l2_rebuild_state/reverse_cites/{targets.jsonl, vault_index.jsonl, prompt.md}`

### E.2 派 1 subagent(opus 4.7)

读 `_l2_rebuild_state/reverse_cites/prompt.md`(完整指令含 cites_basis 严格定义、output schema、约束),subagent 输出写到 `_l2_rebuild_state/reverse_cites/results/results.jsonl`。

### E.3 应用(`apply --stage rev_cites`)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage rev_cites
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

强制 `rel == cites_basis`,过滤 dangling pid + self-loop + 防重 by (from, to),写入 `1_extracted/relations/cites_basis.jsonl`,然后刷反链页 / 主题 / regions / global_index。

---

## 4c. Trigger F: rel_judge_rerun(2026-05-06 加入,isolated 政策一次清账)

诊断:跑 `relations_coverage_metric.py` 看 isolated 政策清单(0 inbound + 0 outbound)。这些政策可能是:
  - **真孤儿**:政策本身边缘 / 行业目录,vault 内确无关联(承认是孤儿即可)
  - **召回不足**:旧 prompt rel_judge 没识别出与 vault 内某些政策的真实 5 类关系

trigger F 用 LLM(新 prompt + 新模型)对每个 isolated 政策从 outbound 视角重审 5 类关系,**0 边输出 acceptable**(不会强迫 LLM 硬编)。同时通过履历表(§4d)记录"已审"标记,后续 metric 看到 isolated 时能区分"已审 + 真孤儿" vs "未审"。

### F.0 目标选择规则(2026-05-06 扩展)

trigger F 不只针对 isolated(双 0)。`inbound_only + 较新政策` 也是召回不足高嫌疑子集 — 一个 2025+ 新政策被引用却 outbound=0,几乎肯定不是真无关联(它至少应 cites_basis / aligns_with 上位双碳意见 / 新型电力系统行动方案等),而是旧版 rel_judge 召回不足。

**正确的 trigger F 候选清单**:
```python
candidates = isolated  # 双 0 政策(metric quadrants.isolated)
       ∪ {p ∈ inbound_only : year(p) ≥ 2025 AND
                              history(p).trigger == 'build_phase_legacy'}
```

实操命令:
```bash
python3 -c "
import json, subprocess
m = json.loads(subprocess.run(['python3','_meta/scripts/relations_coverage_metric.py','--json'],
    capture_output=True, text=True).stdout)
hist = {}
import pathlib
for line in pathlib.Path('_meta/audit/rel_judge_history.jsonl').read_text().splitlines():
    if line.strip():
        try:
            r = json.loads(line); hist[r['pid']] = r
        except: pass

isolated = m['quadrants']['isolated']
inbound_unaudited = [p for p in m['quadrants']['inbound_only']
    if hist.get(p, {}).get('trigger') == 'build_phase_legacy'
    and int(p.split('_')[1]) >= 2025]

candidates = sorted(set(isolated + inbound_unaudited))
print(','.join(candidates))
"
```

完整 3 步:

### F.1 准备(`prepare`)

```bash
# 拿 isolated 清单
python3 _meta/scripts/relations_coverage_metric.py --json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(','.join(sorted(d['quadrants']['isolated'])))
" > /tmp/isolated_pids.txt

# 派活
PIDS=$(cat /tmp/isolated_pids.txt)
python3 _meta/scripts/rebuild_l2.py prepare --trigger rel_judge_rerun \
  --pids "$PIDS" --batch-count 3
```

脚本自动:
- 加载 51 isolated 的 raw body 前 20000 字 + 273 vault_index
- 拆 N batch(默认 3,可 `--batch-count` 调,典型 ≤17 pids/batch 让 prompt ≤500k chars)
- stage `_l2_rebuild_state/rel_judge_rerun/{batch_{1..N}.jsonl, vault_index.jsonl, inputs.jsonl, prompt.md}`

prompt 模板**显式写"0 边输出 acceptable"**,防 LLM 为了产出而硬编关系。

### F.2 派 N subagent(opus 4.7,并行后台)

读 `_l2_rebuild_state/rel_judge_rerun/prompt.md`,派 N 个 subagent 各 1 batch(`run_in_background: true` 并行)。每个 subagent 用 Write tool 写 results 到:
- `_l2_rebuild_state/rel_judge_rerun/results/batch_{1..N}.jsonl`
- 同时把整份 jsonl 贴到 final_report ```jsonl 块里(冗余备份,主 session 提取兜底)

### F.3 应用(`apply --stage rel_judge_rerun`)

```bash
python3 _meta/scripts/rebuild_l2.py apply --stage rel_judge_rerun
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

apply 行为:
- 合 N batch results.jsonl
- dangling 校验(from/to 必须 vault 内,from != to,rel ∈ 5 类)
- 按 rel 分组,防重 (from, to) 写入 5 类 `1_extracted/relations/*.jsonl`
- **履历追踪**:对所有 input pid append 履历(包括 0 边的 — 标"已审 + 0 edges")
- post-llm 刷反链 / 主题 / regions / global_index

---

## 4d. LLM 派生履历追踪(2026-05-06 加入,扩展)

vault 维护 3 个 LLM 履历表 + 5C yaml 内嵌审计字段,确保所有 LLM 派生
有时间/版本/模型可追溯。后续 prompt 升版后,可基于履历定向重审旧版数据。

### `_meta/audit/rel_judge_history.jsonl`(关系层)

字段:
```jsonl
{"pid": "P_xxx", "ran_at": "ISO ts", "trigger": "trigger_A_pid_change|trigger_E_reverse_cites|trigger_F_rel_judge_rerun|build_phase_legacy",
 "prompt_version": "v3.1_2026-05-06|unknown_legacy", "model": "claude-opus-4-7|unknown_legacy",
 "edges_outbound_added": int, "edges_inbound_added": int}
```

**自动写入**:apply --stage rel / rev_cites / rel_judge_rerun 末尾自动 append 一行 / 参与本次审的 pid(包括 0 边的)。

**用法**:metric 看 isolated 时 join 履历,知道每 isolated 是:
- `unknown_legacy + edges=0` → 旧版未审过的疑似召回不足(候选 trigger F)
- `trigger_F_rel_judge_rerun + edges=0` → 已用新 prompt 审过 + 真孤儿(无需重审)
- `trigger_A_pid_change + edges>0` → 新政策入库时已审 + 有边(健康)

**backfill 已跑一次**(commit 3cf26cc 起):273 政策都标 `build_phase_legacy + unknown_legacy`,后续每次 trigger A/E/F 跑时再覆盖履历(append,以最近一次为准)。**重复跑 backfill 拒抗**(已含 build_phase_legacy 行就 abort)。

**升级 prompt 时**:改 `REL_JUDGE_PROMPT_VERSION` 常量(`_meta/scripts/rebuild_l2.py` 顶部),后续履历自动标新版本。

### `_meta/audit/stance_history.jsonl`(stance LLM 抽取,2026-05-06 加入)

字段:
```jsonl
{"comment_filename": "X.md", "ran_at": "ISO ts", "trigger": "trigger_B_commentary_change|build_phase_legacy",
 "prompt_version": "v3_source_domain_2026-05-06|unknown_legacy", "model": "claude-opus-4-7|unknown_legacy",
 "stance_pair_total": int, "source_hit_rate": float}
```
自动写入:apply --stage stance 末尾对每参与 commentary append 一行。
backfill 已跑(189 commentaries 标 build_phase_legacy)。

升级 prompt 时:改 `STANCE_PROMPT_VERSION` 常量。

### `_meta/audit/opinions_summary_history.jsonl`(主题观点汇总,2026-05-06 加入)

字段:
```jsonl
{"theme_dir_name": "POWER_MARKET", "ran_at": "ISO ts", "trigger": "...",
 "prompt_version": "v3_wiki_link_2026-05-06|unknown_legacy", "model": "..."}
```
自动写入:apply --stage opinions-summary 末尾对每 fresh 主题 append 一行。

升级 prompt 时:改 `OPINIONS_SUMMARY_PROMPT_VERSION` 常量。

### 5C business_view yaml 内嵌审计字段

每 yaml 含 `extracted_at` / `extracted_by` / `extracted_model`,5C apply 时自动写。
backfill 已跑(10 个缺字段的标 unknown_legacy)。

---

## 4f. Trigger G: classification_apply(2026-05-07 加入,分类标记下架)

诊断:trigger F 已对 isolated 政策出 LLM 分类(label / suggested_action),
其中 `exclude_from_main_graph` 类(news/index_page 等噪声)需要从所有派生层
排除,但**不删除 raw**(LLM Wiki §1 raw immutable)。trigger G 就是把分类
落到 fm + 派生层全自动跳过。

与 trigger A-F 区别:
- 不动 raw body,不动 5C / 关系层
- 只在 raw fm 加 audit metadata(§6.1 「标记下架」协议)
- 改下游 N 个脚本读 helper 一次跳过

完整 3 步:

### G.1 准备 — 分类已就绪

前置:已跑过 trigger F + 已运行 LLM 分类(`isolated_classification.jsonl`
就绪),例如本会话 B7 79 个 exclude_from_main_graph 行。无需 prepare 阶段。

### G.2 应用 fm(SKILL §6.1 「标记下架」协议)

```bash
python3 _meta/scripts/oneshot_apply_classification_tags.py [--dry-run]
```

幂等:重跑不重复加 tag。备份原文件至 `0_raw/_archive/policies/`。

### G.3 派生层全自动跳过(deterministic)

5 下游脚本通过 `_meta/scripts/_isolated_filter.load_exclude_pids()` 单源:

```bash
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
python3 _meta/scripts/build_topic_distribution.py  # 前端 JSON
```

详见 §8d「派生层 isolated 过滤单源模式」。

---

## 4e. trigger E/F 候选自动建议(2026-05-06)

`relations_coverage_metric.py` 加 2 个 flag,基于 metric + 履历自动生成候选:

```bash
# trigger F (rel_judge_rerun) 候选:isolated(year≥2017) ∪ inbound_only 2025+ build_legacy
PIDS=$(python3 _meta/scripts/relations_coverage_metric.py --trigger-f-candidates)
python3 _meta/scripts/rebuild_l2.py prepare --trigger rel_judge_rerun --pids "$PIDS" --batch-count 3

# trigger E (reverse_cites) 候选:UPSTREAM_CANDIDATES 中 cites_basis inbound ≤3 的上位政策
PIDS=$(python3 _meta/scripts/relations_coverage_metric.py --reverse-cites-suggest)
python3 _meta/scripts/rebuild_l2.py prepare --trigger reverse_cites --target-pids "$PIDS"
```

不需要人眼 sample-first 决定哪个政策跑。

---

## 5. LLM Wiki 5 原则速查(每次操作前自查)

| # | 原则 | 操作时检查 |
|---|---|---|
| 1 | **Raw immutable** | 你在写 `0_raw/`?除非是「重抓重入」例外(见 §6),否则停手。如果是写 frontmatter 字段,确认是否在白名单(`related_policy / related_policy_source / not_policy_related / commentary_type`)— 不在白名单就违规 |
| 2 | **派生分层** | L2 通用层 (`1_extracted/`) vs L2 业务私有 (`_meta/business_view/`) — scores / 影响分析 / 行动建议属业务私有,绝不写 raw frontmatter |
| 3 | **Append-only** | 派生发现错了,改派生抽取脚本 + 重跑;**绝不**回灌修改 raw |
| 4 | **可追溯** | 派生文件必须含 `extracted_at` + `extracted_by` + `extracted_model`(本 skill 模板已加) |
| 5 | **可重现** | LLM 任务记 prompt + 模型版本(本 skill 用 `claude-opus-4-7`,prompt 在 prompt.md 留痕) |

**白名单字段**(允许写 raw frontmatter,见 CLAUDE.md §2 例外):
- 政策的 `related: [...]`(L2 关系层结果回填)
- 评论的 `related_policy / related_policy_source / not_policy_related / commentary_type`
- raw 抓取错误的轻量字段修正(如 date 字段错)+ 加 audit 字段

不在白名单的 LLM 生成字段(摘要 / scores / 影响分析 / 价值标签 / 一句话精髓)→ **必须**写派生层。

---

## 6. 「重抓重入」例外协议(body PDF 乱码 case)

当发现 raw body 是 PDF 二进制 / 抓取失败的乱码:

1. **不改 frontmatter 的 fact 字段**(id/title/official/issuer/date)
2. **备份**原文件到 `0_raw/_archive/policies/{filename}__pre_<reason>_<timestamp>.md`
3. **替换 body**(保留 `# title` + metadata 块 + `## 政策原文` 标题,只替换 `## 政策原文` 之后的内容)
4. **加 frontmatter audit 字段**(在 `provenance` 下)
   ```yaml
   provenance:
     # ...原字段保留
     body_refetched_at: '<now ISO>'
     body_refetched_method: pdfplumber|textutil|trafilatura
     body_refetched_from: <下载的 url>
     body_pre_refetch_len: <被替换内容字符数>
   ```
5. 然后走 trigger A 全套(因为 body 变了 → 5C/关系层都要重抽)

详见 `references/body-refetch-pattern.md`。

---

## 6.1 「标记下架」例外协议(2026-05-07 加入,与 §6 并列)

当 LLM 分类标记某 raw 政策为 `exclude_from_main_graph`(news/index_page
等噪声)需要从派生层下架,但**不删 raw**:

1. **不改任何 fact 字段**(id/title/official/issuer/date/region)
2. **备份**原文件到 `0_raw/_archive/policies/{filename}__pre_classification_<ts>.md`
3. **fm 加分类元数据**(audit 范畴,与 fact 字段并列):
   ```yaml
   classification:
     isolated_label: news_or_press|index_page|...
     suggested_action: exclude_from_main_graph
     confidence: 0.0-1.0
     classified_at: <ISO ts>
     classified_by: B7_subagent_v1
   tags:
     - classified_main_graph_exclude   # append 不覆盖
   provenance:
     classification_applied_at: <ISO ts>  # 加 audit 字段
   ```
4. **body 一字不动**
5. 然后跑 trigger G(§4f)让派生层全自动跳过

与 §6「重抓重入」差别:
- §6 改 body(因 PDF 乱码)→ 必须重跑 5C / 关系层
- §6.1 不改 body,只加 audit metadata → 派生层 deterministic 跳过即可,
  无需 LLM subagent

可逆:删 fm.classification + 移除 fm.tags 中 marker → 政策即恢复全派生层
可见。

---

## 7. 加新主题(L2 themes 扩容)

新主题(如 RURAL_REVITALIZATION)只需改 1 处:

```bash
# 1. 编辑 _meta/themes_registry.yaml 加一块
# 2. 编辑 1_extracted/entities/registry.yaml 加 type=[theme] entry(同 id)
# 3. 跑 deterministic post-llm
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

`crystallize_theme.py --all` 会自动循环 registry 中全部主题。

---

## 8. 常见漏跑 / 陷阱(本会话踩过的坑)

| 陷阱 | 表现 | 防止 |
|---|---|---|
| 关系层 LLM judge 漏跑 | 新政策 `cites_basis / iterates / extends / clarifies / aligns_with` 全 0 边,在 graph 里几乎是孤岛 | 必须 trigger A.2 派 rel_judge subagent |
| opinions-summary.md 漏跑 | `crystallize_theme.py` 不写它(脚本注释明说),frontmatter `last_updated` 没刷新 | 必须 trigger B.4 派 opinions-summary subagent |
| L3 工具链读 raw 旧字段 | `timeline.md "重要性≥4 = 0"` — 因 L1.2 把「重要性」迁到 business_view yaml,但脚本还读 raw fm | 已修复(crystallize/global/regions 改读 yaml),但若新写 L3 脚本注意同样 pattern |
| stance source domain 缺失 | LLM 输出 `source: "?"`,共识门槛 ≥3 distinct domain 命中率低 | 在 stance prompt 强制提取 source domain(已加进 prompt.md) |
| stance batches 与 commentary 集合不对齐 | filter 时大量 drop_unknown(comment_filename 找不到对应 vault 文件) | 重抓而不是 filter;或确认 stance batches 与当前 commentary 同源 |
| 14 PDF 重抓时 P_2024_TJ_01010970 title-body 错配 | URL 指向其他文件,内容与 title 不符 | 重抓后 LLM 应 flag,人工 audit |
| 入库政策 fm 缺必填字段 | source_type / region.level / provenance.url 缺,L3 渲染崩 | trigger A step 0 前置 audit `validate_l1.py --pid` 已自动跑(2026-05-06)阻断 |
| 入库政策 body 是 PDF 二进制 / HTML 残留 | body_audit 抓不到关键词,5C 摘要乱码 | trigger A step 0 前置 `oneshot_l1_body_audit.py --pid` 已自动跑(2026-05-06) |
| reclassify 评论 fm 残留 LLM 派生字段 | 14 篇 commentary 带 `_migrated_from + scores + 重要性`,违 LLM Wiki §1 | `oneshot_l12_residue_audit.py` 全量 audit 可发现;trigger A 前置覆盖政策侧 |
| LLM 幻觉一个不存在的 pid 写进 jsonl | 反链页指向不存在的 pid,graph 出现 dangling 边 | apply_rel / apply_rev_cites 已加 `_load_vault_pid_set()` dangling 校验(2026-05-06) skip + 警告 |
| 5C subagent 输出 scores 不全或 D1-D6 越界 | apply 进派生层后 yaml 字段污染 / L3 渲染逻辑错 | apply_5c 已加 schema 强校验(2026-05-06)— pid/summary/scores 6 维/影响分析 4 段缺即阻断 |

---

## 8b. pre-commit hook(2026-05-06 加入)

防 baseline 倒退闸 — 阻止 commit 引入新 schema 违规政策:

```bash
# 安装(在 vault 根 cd 下跑一次)
cp _meta/git_hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

hook 行为:
- 仅扫 staged 的 `0_raw/policies/*.md`(评论 baseline 漂移多,本 hook 不卡评论)
- 提取每个 staged 政策的 fm.id,跑 `validate_l1.py --pid X,Y --strict`
- 任一 error/warn → 阻断 commit(strict 模式 warns 也升 error)
- 临时跳过:`git commit --no-verify`(仅 baseline 修复 commit 用)

hook 不会让既有违规 commit 越来越多 — 只阻断**新引入**的违规。

## 8c. 派生文件命名约定 — 防 wiki link alias 冲突(2026-05-06 加入)

**背景**:Obsidian wiki link 解析优先级是**文件名 > alias**。如果派生文件用 `P_xxx.md` 命名,会与 raw 政策的 `aliases: [P_xxx]` 冲突 — 所有 `[[P_xxx]]` 引用被派生文件"截胡",raw 政策在 graph view 显示孤立(即便有 5+ 关系边)。

**修复(已生效)**:派生文件统一加前缀:
- 反链页 `1_extracted/relations/_index_by_policy/_rev_P_xxx.md`(build_reverse_links.py)
- opinion 聚合页 `1_extracted/opinions/_op_P_xxx.md`(aggregate_opinions.py)
- diff 页本来就是 `P_xxx__from__P_yyy.md` 格式,**不冲突**(无需改)

**新写派生文件脚本时的命名规则**:
- 输出文件名**不可**精确等于 `P_\d{4}_[A-Za-z0-9_]+`(raw 政策 alias 模式)
- 必须加前缀(`_rev_` / `_op_` / 其他语义前缀)或后缀
- 派生页若是"关于某 raw 政策"的(反链页 / opinion 矩阵等),body 顶部加显式 [[<file_stem>|<显示名>]] link 兜底 graph view
- 派生页若是"关于某主题/汇总"的(opinions-summary 等),末尾加"# 关联政策清单(graph 兜底)"段列举所有相关政策的 [[<file_stem>|<pid>]]
- 入库前用以下脚本验证全 vault 无冲突:
  ```python
  import re
  from pathlib import Path
  ALIAS_PATTERN = re.compile(r'^P_\d{4}_[A-Za-z0-9]+(?:_[a-zA-Z0-9]+)?$')
  for p in Path('.').rglob('*.md'):
      if '.git' in p.parts: continue
      if ALIAS_PATTERN.match(p.stem):
          print(f'collision: {p}')
  ```

**用户体验改善**:修完后 `[[P_xxx]]` 引用(在 opinions-summary / themes / 其他反链页等)正确解析到 raw 政策原文,而不是派生 hub 页。raw 政策 graph view 显示其全部关系边。

## 8d. 派生层 isolated 过滤单源模式(2026-05-07 加入)

**背景**:B7 LLM 把 132 isolated 政策分类为 5 类 action,79 个 exclude_from_main_graph
需要从所有派生层排除。如果每个脚本各自读 audit jsonl 或 fm,容易出现
"前端跳过 / 后端没跳过"的不一致(本 skill commit e435f96 就是只过滤前端
3 主题,后续会话发现 13 主题 / 反链页 / global_index 都漏过)。

**修复(已生效)**:`_meta/scripts/_isolated_filter.py` 是**单一权威源**:

```python
from _isolated_filter import load_exclude_pids
EXCLUDE = load_exclude_pids()  # 读 _meta/audit/isolated_classification.jsonl
```

5 下游脚本统一接它:
- `crystallize_theme.py`(13 主题 _input.json 排除)
- `build_global_index.py`(仪表盘 policy_count 排除 + 备注)
- `build_reverse_links.py`(from/to 任一是 exclude → 跳边 + commentary_inbound)
- `aggregate_opinions.py`(写 _op_*.md 前 guard,实际命中 0)
- `build_topic_distribution.py`(前端 JSON 重构,删内联读 jsonl)

**单源原则**:fm tag(`classified_main_graph_exclude`)只服务 Obsidian
graph filter(`-#classified_main_graph_exclude`),Python 脚本一律读 jsonl。
这避免"fm 改了 jsonl 没改"或反向不一致。

**新写派生脚本时**:任何枚举 vault 政策的下游脚本(L2 派生 / L3 结晶 /
business_view / 前端导出)都要 import helper 一次过滤。验证 checklist:

```bash
# 改完后跑这个验证 0 个 exclude pid 进派生
python3 -c "
import sys; sys.path.insert(0, '_meta/scripts')
from _isolated_filter import load_exclude_pids
exclude = load_exclude_pids()
# 查派生层文件 / json 中 pid 是否含 exclude
"
```

**第二层兜底 — 派生页加显式 [[<raw 文件名>]] link**:

Obsidian alias resolution 在 graph view 不一定可靠(用户实测,即便 alias 有效,graph 中 raw 政策仍可能显示孤立)。第二层兜底:派生层文件 body 顶部加一行显式文件名 link:

```markdown
> 政策原文:[[<raw 政策真实文件名 stem>|<显示名>]]
```

`[[<file_stem>]]` 用真实文件名(不是 alias),Obsidian 100% 解析为 raw 政策文件,graph view 必然建边。

实施位置(已加):
- `build_reverse_links.py` 反链页 frontmatter 后第一行
- `aggregate_opinions.py` opinion 矩阵页 frontmatter 后第一行

写新派生层文件脚本时,如果该页面是"关于某 raw 政策的派生",同样应加这行显式 link。

---

## 9. 不要做的事

- ❌ 用 `git add .` 或 `git add -A`(可能纳入 macOS cruft / 临时文件;用具体路径)
- ❌ 修改 raw frontmatter 非白名单字段(违 LLM Wiki §1)
- ❌ 跳过 prepare 直接跑 apply(staging 数据缺失)
- ❌ 派 subagent 时写 vault 内任何路径**除了** `2_crystallized/`(opinions-summary 例外)
- ❌ 删 `_l2_rebuild_state/_pre_*_backup/`(回滚保险)
- ❌ 在用户没明说时 commit(CLAUDE.md "提交节奏:用户明确要求才 commit")
- ❌ 用 console API key 模式(`derive_business_view.py` 直接跑)— 用户是 Max 订阅无 API key,必须走 subagent

---

## 10. 速查 — 命令 cheatsheet

```bash
# 入口
python3 _meta/scripts/rebuild_l2.py --help

# trigger A (新政策 / body 重抓)
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids P_xxx,P_yyy
# (派 2 subagent: 5c, rel_judge)
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm

# trigger B (评论变)
python3 _meta/scripts/rebuild_l2.py prepare --trigger commentary_change --all-commentaries
# (派 4 subagent: stance batch_{1..4})
python3 _meta/scripts/rebuild_l2.py apply --stage stance
# (派 3 subagent: opinions-summary spec_{1..3})
python3 _meta/scripts/rebuild_l2.py apply --stage opinions-summary

# trigger C/D (deterministic only)
python3 _meta/scripts/rebuild_l2.py deterministic --scope all
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
python3 _meta/scripts/rebuild_l2.py deterministic --scope themes

# trigger E (反向 cites_basis,T4 模式)
python3 _meta/scripts/rebuild_l2.py prepare --trigger reverse_cites \
  --target-pids P_2024_GO_L775,P_2018_NDRC_364,P_2024_NDRC_20
# (派 1 subagent: reverse_cites)
python3 _meta/scripts/rebuild_l2.py apply --stage rev_cites
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm

# trigger F (isolated 政策一次清账)
PIDS=$(python3 _meta/scripts/relations_coverage_metric.py --json | python3 -c "
import json, sys
d = json.load(sys.stdin); print(','.join(sorted(d['quadrants']['isolated'])))
")
python3 _meta/scripts/rebuild_l2.py prepare --trigger rel_judge_rerun \
  --pids "$PIDS" --batch-count 3
# (派 N subagent: rel_judge_rerun batch_{1..N},opus 4.7,并行后台)
python3 _meta/scripts/rebuild_l2.py apply --stage rel_judge_rerun
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm

# trigger G (分类标记下架,§4f)
python3 _meta/scripts/oneshot_apply_classification_tags.py [--dry-run]
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
python3 _meta/scripts/build_topic_distribution.py  # 前端 JSON

# 履历追踪(3 个表)
ls _meta/audit/{rel_judge,stance,opinions_summary}_history.jsonl

# trigger F / E 自动候选建议
python3 _meta/scripts/relations_coverage_metric.py --trigger-f-candidates
python3 _meta/scripts/relations_coverage_metric.py --reverse-cites-suggest
# 看 isolated 政策的"已审"状态
python3 -c "
import json
hist = {}
with open('_meta/audit/rel_judge_history.jsonl') as f:
    for line in f:
        r = json.loads(line); hist[r['pid']] = r  # 保留最新一行
# 报 trigger=build_phase_legacy + edges=0 的 pid(候选 trigger F)
"

# 独立审计工具(可单跑或被 trigger A step 0 自动调用)
python3 _meta/scripts/validate_l1.py [--pid X,Y] [--strict] [--json]
python3 _meta/scripts/oneshot_l1_body_audit.py [--pid X,Y] [--json]
python3 _meta/scripts/oneshot_l12_residue_audit.py [--pid X,Y] [--json]
python3 _meta/scripts/relations_coverage_metric.py [--json] [--isolated-list]

# 单主题(本 skill 一般不用,registry --all 更省事)
python3 _meta/scripts/crystallize_theme.py --theme power_market --aliases "电力市场,电力交易" --theme_zh "电力市场"

# 查看现状(在做任何决策前)
git log --oneline -5
git status --short | awk '{print $2}' | sed 's|/.*||' | sort | uniq -c
ls -la _l2_rebuild_state/ 2>/dev/null  # 看是否有未完成的 staging
```

---

## 11. 决策树(快速归类)

```
用户提到此 vault 改动
    │
    ├─ 改了 0_raw/policies/?  ─── YES ──→ trigger A (pid_change)
    │   (prepare 自动跑 step 0 前置 audit:validate_l1 / body_audit / residue_audit
    │   任一 error 阻断;通过后才进 5C / rel_judge / post-llm)
    │
    ├─ 改了 0_raw/commentaries/ frontmatter? ─── YES ──→ trigger B (commentary_change)
    │
    ├─ 手动加 supersedes / 关系边 / dedup? ─── YES ──→ trigger C (deterministic post-llm)
    │
    ├─ 关系层覆盖率 metric 显示某上位 pid inbound 偏低/=0? ──→ trigger E (reverse_cites)
    │   (跑 relations_coverage_metric.py 看上位政策 inbound section,
    │   选 inbound ≤ 3 的几个作 target-pids)
    │
    ├─ isolated 已分类 + 部分要从派生层下架(news/index 噪声)? ──→ trigger G (classification_apply,§4f)
    │   (分类已就绪 → oneshot_apply_classification_tags + deterministic post-llm)
    │
    ├─ 关系层 metric 报 isolated 政策(0 in + 0 out)? ──→ trigger F (rel_judge_rerun)
    │   (查 _meta/audit/rel_judge_history.jsonl 看 isolated 政策是否已用
    │   新 prompt 审过;若大多数仍 build_phase_legacy,trigger F 一次清账)
    │
    ├─ 提到 stale (opinions / themes / 反链 / 主题)? ──→ 看哪一层 stale
    │   ├─ opinions / opinions-summary stale ──→ trigger B
    │   ├─ themes timeline / regional 所有都旧 ──→ trigger D 全跑
    │   └─ 仅反链页 stale ──→ build_reverse_links.py 单跑
    │
    ├─ 想全量校验 vault 数据合规? ──→ 跑 4 个 audit 工具(无需 trigger):
    │   ├─ validate_l1.py(fm 必填 / enum)
    │   ├─ oneshot_l1_body_audit.py(body 质量)
    │   ├─ oneshot_l12_residue_audit.py(LLM 派生字段残留)
    │   └─ relations_coverage_metric.py(关系层覆盖率 + derives_from to=null)
    │
    ├─ 想全量重跑 deterministic? ──→ trigger D (deterministic --scope all)
    │
    └─ 不确定? → 默认 trigger D 跑 deterministic --scope all 兜底
                  (deterministic 是幂等的,跑多次无害)
```

---

## 参考资料

- `references/subagent-prompts.md` — 各 subagent prompt 模板细节(rebuild_l2.py 自动 stage,但要改 prompt 看这里)
- `references/body-refetch-pattern.md` — PDF 乱码重抓详细协议(本会话 14 篇案例)
- `references/llm-wiki-rules.md` — LLM Wiki 5 原则 + 白名单字段全清单(摘自项目 CLAUDE.md §2)
- vault 内 `CLAUDE.md` — 项目级权威规则(本 skill 是它的执行手册)
- vault 内 `_meta/schema_v3.md` — 9 类关系 + jsonl schema 权威规范

如本 skill 与 CLAUDE.md 冲突,**以 CLAUDE.md 为准**。
