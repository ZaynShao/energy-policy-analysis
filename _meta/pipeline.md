---
title: L2 派生管道
date: 2026-04-26
schema_version: 3.0
---

# L2 派生管道

> 服务对象:`policy-watch` skill 的 daily-scan / weekly-reverse-scan 自动调度。
> 哲学:raw → extracted → crystallized → lints,**raw 永远是 source of truth,extracted 全删能重建**。

---

## 完整管道图(daily 模式)

```
L1 daily-scan 完成
   ├─ 0_raw/policies/<filename>.md   新政策入库(v2 minimal frontmatter)
   └─ 0_raw/commentaries/<filename>.md  新评论入库
        │
        ▼
[L2-1] frontmatter 升级 v2 → v3                     `_meta/scripts/upgrade_frontmatter_v2_to_v3.py`
        ├─ 生成 id (P_<year>_<issuer_short>_<num>)
        ├─ provenance 嵌套化
        ├─ region 结构化(level/code/name)
        └─ ID 碰撞 _a/_b/_c 后缀化
        │
        ▼
[L2-2] entity alias 抽取                              `_meta/scripts/extract_entities.py`
        ├─ 读 registry.yaml
        ├─ alias substring 匹配(长度优先)
        ├─ → 1_extracted/entities/_extractions.jsonl
        └─ → 1_extracted/entities/<type>/<id>.md (反链页)
        │
        ▼
[L2-3] 关系抽取(regex)                                `_meta/scripts/extract_relations_regex.py`
        ├─ 文号反向索引
        ├─ supersedes(显式废止关键词 + date sanity check)
        ├─ references(剩余文号引用)
        ├─ sibling/同文号过滤
        └─ → 1_extracted/relations/{supersedes,references}.jsonl
        │
        ▼
[L2-4] 关系抽取(启发式)                              `_meta/scripts/extract_relations_heuristic.py`
        ├─ 候选对生成(共享 ≥2 entity)
        ├─ clarifies(标题"细则/指引" + 引用)
        ├─ iterates(同部委 + 标题相似 0.5≤sim<0.95 + 时差 ≥3 月)
        ├─ extends(共享 ≥6 entity + region 跳变 + 时序)
        ├─ aligns_with(共享 ≥4 entity + 同 region 级别 + 不同 issuer + sim ≥0.2)
        └─ → 1_extracted/relations/{clarifies,iterates,extends,aligns_with}.jsonl
        │
        ▼
[L2-5] daily lint                                     `_meta/scripts/lint.py daily`
        ├─ 必填字段 / id 唯一 / 关系 dangling / region code 一致 / diff 覆盖
        └─ → 3_lints/daily/<YYYY-MM-DD>.md  (有 error 推决策频道)
        │
        ▼
完成。仅当 daily lint clean 才触发后续派生(diff/opinion/theme)。
```

---

## 完整管道图(weekly 模式,补 daily 之外的深度派生)

```
[L2-W1] weekly lint                                   `_meta/scripts/lint.py weekly`
   ├─ 双向反链 / 孤儿 canonical / extends 方向校验
   ├─ 同文号不同 base id(数据重复) / opinion 覆盖率
   └─ → 3_lints/weekly/<YYYY-MM-DD>.md
        │
        ▼
[L2-W2] diff 抽取(LLM)— 对新增 supersedes/iterates/extends 跑
   ├─ 输入:本周新增的演进对
   ├─ LLM 抽 diff(维度 / old / new / 影响 / 滴滴三业务)
   └─ → 1_extracted/diffs/<new_id>__from__<old_id>.md
        │
        ▼
[L2-W3] opinion 抽取(LLM)— 对本周新增评论跑
   ├─ 输入:0_raw/commentaries/ 新增
   ├─ LLM 抽 stance(polarity 4 档 / aspect / claim / evidence_quote / confidence)
   └─ → 1_extracted/opinions/<policy_id>.md(政策舆论矩阵,共识/分歧/中性观察/待跟进)
        │
        ▼
[L2-W4] conflicts_with(LLM,严选)— 仅扫 ≥4 分政策对
   ├─ 共享 ≥3 entity + 标题主题接近
   ├─ LLM 严格判:90% 应返回 no-conflict
   └─ → 1_extracted/relations/conflicts_with.jsonl
        │
        ▼
[L2-W5] 主题结晶页派生                                  (脚本待写)
   ├─ 对每个 theme(V2G / 充电基建 / 电力市场 / ...)
   ├─ 聚合关系图 + 时间线 + 区域矩阵 + 舆论汇总
   └─ → 2_crystallized/themes/<theme>/{overview,timeline,regional-coverage,opinions-summary}.md
        │
        ▼
[L2-W6] registry 增量 review                            (脚本待写)
   ├─ _review_queue.yaml 中的实体词 LLM 自判
   ├─ confidence ≥0.85 自动入 registry / < 0.85 留人工
   └─ → registry.yaml 更新 + review_queue 增量
```

---

## 调用约定

### cron 入口(post daily-scan)

policy-watch skill 在 daily-scan 末尾追加:

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析" && \
python3 _meta/scripts/upgrade_frontmatter_v2_to_v3.py && \
python3 _meta/scripts/extract_entities.py && \
python3 _meta/scripts/extract_relations_regex.py && \
python3 _meta/scripts/extract_relations_heuristic.py && \
python3 _meta/scripts/lint.py daily
```

退出码:
- `0` clean
- `1` warning(信息推决策频道)
- `2` error(管道暂停,运维介入)

### 全量重建口令

L2 派生层全删重跑:

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析" && \
rm -rf 1_extracted/{entities/orgs,entities/stakeholders,entities/concepts,entities/regions,entities/themes,entities/_extractions.jsonl,entities/_summary.md,relations/*.jsonl,diffs,opinions} && \
python3 _meta/scripts/extract_entities.py && \
python3 _meta/scripts/extract_relations_regex.py && \
python3 _meta/scripts/extract_relations_heuristic.py
```

`registry.yaml` 不删(canonical 词表是手工/Agent 维护资产,不是派生)。

---

## 现状(2026-04-26 第一阶段建设期)

### 已实施
- ✅ schema_v3.md 正式文档
- ✅ frontmatter v2→v3 升级(357 政策全部)
- ✅ entity 抽取(264 alias → 88 canonical,353 政策命中)
- ✅ regex 关系抽取(supersedes 1 / references 162)
- ✅ 启发式关系抽取(clarifies 53 / iterates 2 / extends 12 / aligns_with 15)
- ✅ diff 抽取(15 个,Agent LLM)
- ✅ daily/weekly lint
- 🚧 opinion 抽取(进行中)
- 🚧 V2G 主题结晶 demo

### 未实施(后续阶段)
- conflicts_with(LLM 严选)
- registry 增量 review(_review_queue 处理)
- 主题结晶页生成器(目前 V2G demo 是手工 Agent)
- 混合搜索(BM25 + 向量 + 图遍历)

### 已知数据问题
- **6 组同文号不同 base id**(数据重复入库,~13 篇政策需 dedup)
- 7 篇零实体命中政策(召回缺口,等 LLM 补抽)
- 27 孤儿 canonical(backup 残余,30 天后归档候选)

---

## 与 L1 的接口约定

L1(policy-watch)只管:
- 写 `0_raw/policies/<filename>.md`(v2 minimal frontmatter 即可)
- 写 `0_raw/commentaries/<filename>.md`
- 不要写到 `1_extracted/`(派生层禁止 L1 直接写入)
- 不要在 raw frontmatter 写关系字段(`supersedes/iterates/related` 等,会被 L2 升级时丢弃)

L2 派生(本管道):
- 只读 `0_raw/`
- 写 `1_extracted/` / `2_crystallized/` / `3_lints/`
- 全幂等:任何步骤都允许重跑

---

## 常见维护指令

```bash
# 跑 weekly lint 看健康度
python3 _meta/scripts/lint.py weekly

# 看某条政策的所有关系
grep -h "P_2024_NDRC_718" 1_extracted/relations/*.jsonl

# 看某 canonical 的反链页
ls 1_extracted/entities/stakeholders/charging_operator.md

# 看某政策的演进 diff
ls 1_extracted/diffs/ | grep P_2025_NDRC_1656

# 看某政策的舆论矩阵
cat 1_extracted/opinions/P_2024_SC_12_a.md
```

---

_v1.0 · 2026-04-26 · 与 schema_v3 同步落地_
