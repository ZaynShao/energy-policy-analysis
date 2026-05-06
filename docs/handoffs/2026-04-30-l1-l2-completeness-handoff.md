---
date: 2026-04-30
session_end_commit: 82bed6f
next_session_focus: L1+L2 信息完整性优化(脱离 L3 输出效果)
estimated_total_work: ~3 天(Tier 1 1.5-2 天 + Tier 2 1-1.5 天)
---

# L1+L2 完整性优化 Handoff

## 背景

上一会话(2026-04-30,共 13 commits)做完了 P3-P8 全套 staleness 修复 + 编排器固化 + skill 沉淀,vault 进入"形式合规但内容有空隙"状态。本次 handoff 转入**纯 L1+L2 完整性优化**,**不考虑 L3 输出效果**(月报 / 趋势 / opinions-summary 渲染暂搁置)。

## 当前 vault 状态(82bed6f 时)

```
L1 政策 271
L1 评论 283 (191 linked / 52 not_policy_related / 40 thematic_no_link)
L2 关系 9 类边总数:
  cites_basis 58 / supersedes 7 / iterates 24 / extends 9 / clarifies 73 /
  references 140 / aligns_with 41 / conflicts_with 0 / derives_from 96
L2 entities 67 entity pages (含 6 theme entity)
L2 business_view yaml 271 (5 篇缺 scores 待 review)
L2 policy_summaries.jsonl 271 (~)
L2 opinions/<pid>.md 79 篇 (29% 政策覆盖)
L3 主题 9 (含本会话新加 carbon_market_theme)
L3 反链页 ~213 (双向 + commented_by)
```

## 必读文档(新 session 第一件事)

按顺序读:

1. **`CLAUDE.md`**(项目级权威规则,LLM Wiki 5 原则 + 白名单字段)
2. **`.claude/skills/policy-vault-l2-rebuild/SKILL.md`**(L1→L2 维护协议,本会话沉淀)
3. **本文档**(handoff)
4. 参考:`_meta/schema_v3.md`(数据 schema 权威)
5. 参考:`docs/handoffs/2026-04-30-l1-3-gap-candidates.md`(L1.3 backlog)

## 上轮已完成(不要重做)

- P3 反链双向化 + commented_by 段
- P4 评论 LLM 正文研判(282 评论 frontmatter 重判)
- P5 opinions filter + P5b stance 全量重抽 + P5c opinions-summary 重生成
- P6 W1+W2 8 篇关系层 LLM judge(只 outbound)
- P7 entities + crystallize 全主题 + regions + global_index + reverse_links
- P8 rebuild_l2.py 编排器 + themes_registry + crystallize --all
- L1.3 W1 充电+乡村 3 篇 + W2 真高 ROI 5 篇入库
- 14 PDF 乱码 raw 重抓
- L3 工具链 bug 修复(crystallize/global/regions 读 business_view 重要性)
- skill 沉淀 .claude/skills/policy-vault-l2-rebuild/

---

## TODO 执行顺序(按本次 handoff 优先级)

### 阶段 1: lint + audit + metric 闭环(最快路径,~2 天)

> 目的:**先建 metric,让数据告诉你哪里弱**,而不是凭直觉排序

#### T1 [30 min] L1 frontmatter lint 工具

```
新建: _meta/scripts/validate_l1.py
功能:
  - 政策 frontmatter 必填字段:id / title / date / region / provenance.url
  - 政策字段值 enum:source_type ∈ {A,B,C,D,E},region.level ∈ {国家,省,市,区}
  - 评论 frontmatter 必填:title / source_url / date_published
  - 评论字段值 enum:commentary_type / related_policy_source 命名规范
  - audit 字段 timestamp ISO 格式校验
输出: lint 报告 stdout + exit code 非 0 当有违规
可选: .git/hooks/pre-commit 自动跑
```

#### T2 [1 h] L1.2 净化残留 audit

```
新建: _meta/scripts/oneshot_l12_residue_audit.py
功能:
  - 扫 raw frontmatter 是否含违规字段:scores / 重要性 / 影响分析 /
    价值标签 / 行动分类 / didi_impact_one_liner
  - 扫 raw body 是否含品牌词:滴滴 / 能链 / 小桔 etc
  - 排除已知例外(_archive/ 下的备份)
输出: 违规清单 + 建议处理(净化 or 例外申报)
```

#### T3 [2 h] raw body 质量全库 audit

```
新建: _meta/scripts/oneshot_l1_body_audit.py
功能:
  - 扫 271 篇 raw body:
    * PDF binary 残留(%PDF / endobj / endstream)
    * HTML 标签残留(过多 < > 标签)
    * body 过短(< 200 字)
    * body 异常长(> 1MB,可能含 base64 图片)
    * title 关键词(jieba 切前 5 词) vs body 前 1000 字关键词重合度
      → 重合度 < 0.3 标记为可疑(P_2024_TJ_01010970 类错配)
输出: 可疑政策清单(预计 5-10 篇)+ 建议处理路径(重抓 or 接受)
```

#### T6 [1 h] L2 关系层覆盖率 metric

```
新建: _meta/scripts/relations_coverage_metric.py
功能:
  - 9 类关系各自:inbound/outbound 政策数 + 入度/出度分布
  - isolated 政策清单(无任何关系边的政策)
  - 上位政策(被多政策 cites_basis/clarifies)的反向边覆盖率
  - to=null 占比(derives_from 等可能 vault 缺上游)
输出: metric 报告 markdown,作为后续 T4/T5 优先级依据
```

#### T13 [10 min] derives_from to=null metric

合并到 T6 一起跑(同 metric 工具)。

#### 阶段 1 完成后做决策

读 T1-T6 输出报告,**让数据决定**下面这些 Tier 1 任务的优先级:
- T4 反向 cites_basis(如 T6 显示 inbound 严重不足)
- T5 conflicts_with 全扫(如想验证 0 边)
- T7 L1.3 Tier A 剩 2 条补完(如 demand-pull 实际遇到)

---

### 阶段 2: 缺口补全 + 验证(~1 天)

#### T4 [2 h] 基础大法反向 cites_basis 全量扫

```
扩展 _meta/scripts/rebuild_l2.py 加 reverse_scan 模式:
  python3 rebuild_l2.py prepare --trigger reverse_cites --target-pids X,Y,Z
  → stage subagent 任务:对每个 target,扫所有 vault 政策 body 是否引用 target

候选上位政策(~10 个):
  P_2024_GO_L775(暂行条例 775 令)
  P_2024_NDRC_15(电力市场基本规则 15 号令,已被 20 号令 supersede)
  P_2024_NDRC_20(电力市场基本规则 20 号令)
  P_2023_GO_19_b(国办发 19 号 充电基础设施体系)
  P_2023_NDRC_545(充电下乡 545 号)
  P_2020_GO_39_b(新能源汽车产业规划 国办 39 号)
  P_2018_NDRC_364(电力系统调节能力指导意见 364 号)
  P_2024_NDRC_0806117c(新型电力系统行动方案)
  P_2022_NDRC_032146fe(十四五新型储能方案)
  P_2021_SC_23(2030 前碳达峰行动方案)

派 1 subagent → apply 新 cites_basis 边
```

#### T5 [半天] conflicts_with 全量扫

```
派 1 subagent 跑 271 政策两两扫(预过滤候选对再 LLM judge)
预过滤:同主题(基于 entities 命中)+ 时间重叠 + issuer 相同 → 候选对
LLM judge: 候选对中是否有 supportive vs critical / 限制 vs 鼓励 等冲突信号
输出: 真冲突边 → write conflicts_with.jsonl(可能仍是 0,但已 audit 通过)
```

#### T7 [3 h] L1.3 Tier A 剩 2 条补完

```
A1: 节能装备高质量发展实施方案(2026—2028 年)— 工信部等四部门
A3: 关于开展零碳园区建设的通知(2025-06)— 国家发改委等

走标准 L1.3 流程:
  1. 派 subagent 搜官方源 → curl + 解析 → 写 _l1_3_w3/drafts/{pid}.md
  2. 用 _l1_3_w1/migrate_to_vault.py 模式迁入 0_raw/policies/
  3. python3 rebuild_l2.py prepare --trigger pid_change --pids ...
  4. 派 subagent 跑 5C + rel_judge → apply
  5. python3 rebuild_l2.py deterministic --scope post-llm
  6. commit
```

---

### 阶段 3: 数据质量量化(~1.5 天)

#### T8 [半天] business_view 影响分析抽样 30 篇 audit

```
样本:20 篇 D1≥4 高重要性 + 10 篇随机 D1<3
人工评分:每段(加油/充电/电力/乡村)1-5 分
出 audit 报告:
  - 平均分 / 中位数 / 各业务方向均分
  - <3 分的样本清单 + 错误类型(空泛/事实错/品牌词残留)
决策:
  - 平均 ≥3.5 → 接受当前 LLM 派生质量
  - <3.5 → 重 5C prompt + 重跑(优先重跑 D1≥4 那批)
```

#### T9 [半天] policy_summaries 同 30 篇样本审

合并 T8 同批样本,同时审 summary / one_liner / reading_value 质量。

#### T10 [2 h] stance LLM source 提取改进 + 重跑 P5b

```
改 .claude/skills/policy-vault-l2-rebuild/references/subagent-prompts.md
  和 _meta/scripts/rebuild_l2.py 的 _stance_prompt_template():
  加规则:"若 source_url 空,从 body 提取作者机构作为 source(如
  '国家能源局答复' → nea.gov.cn,'国网能源院 杨素专访' → eri.sgcc.com.cn)"

跑 P5b 重抽:
  python3 rebuild_l2.py prepare --trigger commentary_change --all-commentaries
  派 4 subagent
  python3 rebuild_l2.py apply --stage stance
不跑后续 opinions-summary(那是 L3 输出范畴)
目标:source 不为 ? 的占比从当前 ~30% → ~70%
```

#### T11 [30 min] business_view 字段 schema 决定

```
决定 didi_impact_one_liner 字段:
  选项 A: 5C prompt 加此字段 → 260 LLM 跑也补 → 字段齐
  选项 B: 废弃此字段 → 11 march 精品也删
建议: A(更有价值,one_liner 是月报段标题候选)
执行: 改 _stage_5c_prompt + 重跑 P5b 全量(或仅 D1≥3 的 ~150 篇)
```

#### T12 [30 min] commentary frontmatter enum 加入 T1 lint

```
在 T1 工具加 enum:
  commentary_type ∈ {A, B, C, D, unknown}  # 验证现有取值,可能要规范
  related_policy_source 命名格式:^(B[1-4]_|manual_).+$
  not_policy_related 必为 boolean
```

#### T14 [30 min] 5 篇缺 scores 政策 review

```
找出 5 篇:
  python3 -c "
  import yaml
  from pathlib import Path
  for f in Path('_meta/business_view').glob('*.yaml'):
    d = yaml.safe_load(f.read_text(encoding='utf-8')) or {}
    if 'scores' not in d or not d.get('scores'):
      print(f.stem)
  "
对每篇:
  - 看 raw 是否真政策(标题/issuer/source_type)
  - 是 → 5C 单跑(派 1 subagent)
  - 不是 → archive 到 _archive/policies/(类型:政策解读/答记者问/报道)
```

#### T15 [30 min] entities 加 RURAL_REVITALIZATION theme entity

```
1. 编辑 1_extracted/entities/registry.yaml,加 type=[theme] entry:
   - id: rural_revitalization_theme
     canonical_name: 乡村振兴
     type: [theme]
     aliases:
       - 乡村振兴
       - 农村
       - 新能源汽车下乡
       - 农村电网
       - 县域充电
       - 农村充电基础设施
2. 跑 extract_entities.py 重抽
3. 不需要加 themes_registry.yaml(那是 L3 主题页范畴,本次 handoff 不做)
   仅让 entities 层能聚合查询乡村相关政策
```

---

## 不做事项(明确不在本次 handoff 范围)

### Tier 3 - 不值得改

- ❌ clarifies 73 边人工全审(LLM v3 judge 整体可信 80%+)
- ❌ references 140 召回率提升到 95%(政策互引天然多样)
- ❌ 历史 v3 LLM judge 关系全审
- ❌ 27 孤儿 entity 清理(无业务影响)
- ❌ 价值标签字段挽救(已废)
- ❌ 271 篇 business_view 影响分析全人工审(30 抽样足够)
- ❌ policy_summaries 全审
- ❌ L1 完整度追求 100%(无穷,demand-pull 是对的)
- ❌ CLAUDE.md 白名单加严格 JSON schema(限制灵活度)

### Tier 3 - 无好办法

- ❌ 评论 source 集中 mp.weixin(上游 RSS 订阅问题,不是 vault 问题)
- ❌ stance polarity 偏 supportive(中国政策评论生态真实写照)
- ❌ business_view 11 march 精品 vs 260 LLM 质量差(人工天花板差距,无法消除)
- ❌ stance LLM 完全可复现(LLM 推理 stochastic,接受 ±5% 抖动)

### L3 范畴(本次 handoff 暂搁置)

- ⏸ L3 趋势/风险展望工具
- ⏸ opinions-summary 重生成(底层 stance 改进后再说)
- ⏸ 加 RURAL_REVITALIZATION 主题页(本次只加 entity,主题页 L3 范畴)
- ⏸ 月报实战(本次专注 L1+L2 数据本身)

---

## 工具速查

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# L2 编排器(已固化)
python3 _meta/scripts/rebuild_l2.py --help
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids X,Y
python3 _meta/scripts/rebuild_l2.py apply --stage 5c|rel|stance|opinions-summary
python3 _meta/scripts/rebuild_l2.py deterministic --scope all|pre-llm|post-llm

# 主题循环
python3 _meta/scripts/crystallize_theme.py --all  # 读 themes_registry.yaml

# 5C 单条派生(若有 ANTHROPIC_API_KEY,但 Max 订阅没有 → 走 subagent)
# Max 订阅模式见 SKILL.md 详述

# git 状态
git log --oneline -10
git status --short | awk '{print $2}' | sed 's|/.*||' | sort | uniq -c

# 反链页 / 主题状态
ls -la 1_extracted/relations/_index_by_policy/ | wc -l
ls -la 2_crystallized/themes/
```

## 关键文件路径

```
本会话产出的工具/文档:
  _meta/scripts/rebuild_l2.py             ← L2 编排主入口
  _meta/themes_registry.yaml              ← 9 主题集中配置
  _meta/scripts/crystallize_theme.py      ← 加 --all 模式
  .claude/skills/policy-vault-l2-rebuild/ ← 维护协议 skill
  docs/handoffs/2026-04-30-l1-3-gap-candidates.md  ← L1.3 backlog
  docs/handoffs/2026-04-30-l1-l2-completeness-handoff.md  ← 本文档

待新建工具:
  _meta/scripts/validate_l1.py                    ← T1
  _meta/scripts/oneshot_l12_residue_audit.py      ← T2
  _meta/scripts/oneshot_l1_body_audit.py          ← T3
  _meta/scripts/relations_coverage_metric.py      ← T6
```

## 提交节奏建议

- 每个 T 完成单独 commit(便于回滚)
- 阶段 1 完成可考虑 squash 为 1 commit "feat(L1+L2 audit): 闭环工具集"
- T8/T9 audit 报告作为 docs/handoffs/2026-04-30-business-view-quality-baseline.md 提交
- 不要在用户没明说时 commit(CLAUDE.md "提交节奏")

## 关键判断准则

每次决策前问 3 句:
1. 这个改动是 L1 还是 L2?(决定 trigger)
2. raw immutable 检查通过吗?(白名单字段 + 重抓重入例外)
3. 是 push 还是 demand-pull?(L1.3 已切 demand-pull,backlog 候选只采高 ROI)

skill `policy-vault-l2-rebuild` 描述会自动触发,跟着 §11 决策树走。
