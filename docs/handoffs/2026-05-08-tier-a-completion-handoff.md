# P2.7 Tier A 完结 handoff — 2026-05-08

## TL;DR

P2.7 Tier A(P0 主题在非 P0 省/national,790 candidates)完整跑完 6 批,**入库 223 政策 / 添 184 边**,vault 体量 674 → 900 政策。8 commits 上 main(`6319fe96` 收官)。

---

## 8 commits 序列

| hash | 主题 | 政策 / 边 |
|---|---|---|
| `febd9e49` | scaffold(切 6 批 + #5 fallback + handoff 接收) | scaffold |
| `18bc7160` | A.1 储能 | +48 / +84 |
| `97b91096` | fix 5C prompt(`is_national_level_originated` 语义) | infra |
| `e0027ade` | A.2 power_market | +38 / +29 |
| `f5c921fe` | A.3 charging_infra | +42 / +11 |
| `20cddeec` | A.4 distribution_grid + A.5/A.6 raw | +38 / +18 |
| `eccb0990` | A.5 v2g+vpp | +46 / +32 |
| `6319fe96` | A.6 aggregator+green+tail(Tier A 完结) | +11 / +5 |

---

## 量化成果

| 指标 | 值 |
|---|---:|
| vault 政策(0_raw/policies/) | **900**(674 → 900,+226) |
| 实际入库派生(business_view) | 223 |
| 关系边总(active) | 1688(P2.7 +184) |
| 真孤立(0 in/0 out) | 155(132 → 155,+23) |
| derives_from backlog(unresolved) | ~80+ |
| junk archived | 216(124 hard pattern + 90 audit-blocked) |
| fetch failed(manual queue) | 177(P0 refetch + Tier A) |
| LLM cost | ~1.5M tokens(opus 4.7 × 12 subagent runs) |

---

## 4 个校准 takeaways(后续直接复用)

### #1 候选 真政策率 ~30-40%
非 P0 省 P0 主题的 candidates 大量是动态/news/会议/解读,非政策本身。Tier A 6 批平均 yield:
- A.1 储能:48 / 145(33%)
- A.2 电力市场:38 / 130(29%)
- A.3 充电:42 / 132(32%)
- A.4 配网:38 / 119(32%)
- A.5 V2G+VPP:46 / 192(24%)
- A.6 长尾:11 / 72(15%)

**对 Tier B / C 估算**:1373 candidates 全做也只能入库 ~400-500 真政策。daily_query 异步消化 Tier C 是合理选择。

### #2 5C `is_national_level_originated` 看 fm.issuer 不看内容
A.1 70% 误判(34/48),修 prompt 后 A.2-A.6 100% 准确:
- 含"省/市/自治区/直辖市" issuer → false → apply 写 derives_from
- NDRC/能源局/工信部/国务院 issuer → true → 无 upstream

修复在 `97b91096`,prompt template `_meta/scripts/rebuild_l2.py::_5c_prompt_template()` 已永久补充语义口诀。

### #3 audit 闸 missing_date 几乎全是 trafilatura 抽不到 body 的网页框架噪声
6 批共 90 个 audit-blocked,标题分析:
- ~70% 是网页框架噪声(长者版/数据/智能搜索/列表索引)— 可直接 drop
- ~20% 是真政策但 trafilatura 抽不到 body(JSP 框架等)— 需 SKILL §A.6.3 fallback chain
- ~10% 是 P_1900_* 文号〔YYYY〕格式不匹配 #5 fallback —少量,可手补

**A.2-A.6 一致性极高**(每批稳定 ~14-29 个 audit-blocked),drop-all 是最划算的策略。

### #4 vault metadata 有 official_number ↔ title 错配(rel_judge 已 conservative 跳过)
A.4/A.5 rel_judge 报告多个 vault entries 的 official_number 与 title 不匹配(例如 P_2021_GO_90633c79 标 1439号但实为新闻文章)。**这是 normalize 阶段历史 bug 累积**,影响 rel_judge 召回。

**未来工作**:扫一次 vault,把 fm.official_number 与 title 显式不匹配的 entries 批量 audit。

---

## 当前 vault 健康指标

```
4 象限:双向 210 / 仅入向 79 / 仅出向 456 / 真孤立 155
反链页期望覆盖(双向 + 仅入向):289
```

isolated 增长 23 个,主要来自 A.3 充电 + A.5 V2G + A.6 长尾(list/news 页本身无 cite)。建议下一轮 reverse_cites trigger 处理。

---

## Pending 工作(优先级序)

### P0 — 短期(本周)
1. **reverse_cites trigger** — 候选:155 真孤立中的 P0 主题政策(尤其 A.5 V2G/VPP 的 ~10 个 isolated),派 reverse_cites subagent 找 inbound 边
2. **derives_from backlog 处理** — `_meta/backlog/derives_from_unresolved.yaml` 累计 ~80 个 to=null,跑 L1.3 demand-pull 重抓未在 vault 的上位 NDRC 文件

### P1 — 中期(本月)
3. **Tier B 启动**(_meta/audit/p2_7_remaining/tier_b_other_theme_p0_prov.jsonl, 242 url)— 京沪苏浙鲁粤的碳市场/设备更新等。预估 ~80-100 真政策入库,LLM ~500K tokens
4. **Tier C 异步**(341 long tail)— 接 daily_query 自然消化,**不一次性做**
5. **vault metadata bug 扫描**(校准 #4)— 写 oneshot 脚本扫 fm.official_number ↔ title 不一致

### P2 — 长期(下月+)
6. **opinions-summary 重生**(commentary 跨 191 篇过期超过阈值后)— Trigger B 全跑
7. **fetch_failed manual queue 处理**(177 url)— 走 SKILL §A.6.3 fallback chain(playwright / archive.org)

---

## 启动 Tier B 时直接复用

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# 1. fetch
python3 _meta/audit_2026-05-06/fetch_candidates.py \
  --candidates _meta/audit/p2_7_remaining/tier_b_other_theme_p0_prov.jsonl \
  --staging 0_raw/policies_staging_b1_2026-05-XX \
  --log _meta/audit_2026-05-06/fetch_p2_7_b.log \
  --concurrency 8

# 2. normalize
python3 _meta/audit_2026-05-06/normalize_to_raw.py \
  --staging 0_raw/policies_staging_b1_2026-05-XX

# 3. quality_drop
python3 _meta/scripts/oneshot_quality_drop.py --batch b1 --apply

# 4. handle audit-blocked(脚本附:见 A.5/A.6 commit)
# 5. prepare
PIDS=$(tr '\n' ',' < _meta/audit_2026-05-06/keep_pids_b1.txt | sed 's/,$//')
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids "$PIDS"

# 6. 派 2 subagent (5C + rel_judge,prompt 已就绪)
# 7. apply
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm

# 8. commit
```

**Tier B 建议切批**:不按主题切(因主题非 P0,目录差异不大),按省切(京沪苏浙鲁粤 6 批,每批 ~40)。

---

## 关联文件

- `_meta/audit/p2_7_remaining/tier_b_other_theme_p0_prov.jsonl` — Tier B 立项
- `_meta/audit/p2_7_remaining/tier_c_long_tail.jsonl` — Tier C 立项
- `_meta/scripts/oneshot_quality_drop.py` — 通用质量过滤(本会话写)
- `_meta/scripts/oneshot_split_tier_a_by_theme.py` — 切批模板
- `_meta/audit_2026-05-06/keep_pids_a*.txt` — 6 批 keep_pids 留存
- `_meta/audit/p2_7_a*_drops_2026-05-08.jsonl` — 6 批 drops 履历
- SKILL §A.6.3 — fetch fallback chain
- SKILL §6.1 — 标记下架协议
- SKILL §8d — 派生层 isolated 过滤
- SKILL §8e — 派生 .md 必须有消费者契约
