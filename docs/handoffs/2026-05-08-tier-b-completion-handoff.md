# P2.7 Tier B 完结 handoff — 2026-05-08

## TL;DR

P2.7 Tier B(非 P0 主题 × P0 省,242 candidates)完整跑完 5 批,**入库 120 政策 / 添 70 边**。同 session Tier A + B 共入库 343 政策(674 → 1020),添 254 边。8 commits 上 main(`453c7a90` 收官)。

---

## Tier B 5 commits 序列

| hash | 批 | 政策 / 边 |
|---|---|---|
| `e03fb1e9` | B.1 广东 | +35 / +30 |
| `4a98198d` | B.2 上海 | +22 / +4 |
| `a677a464` | B.3 北京 | +22 / +16 |
| `b89425fc` | B.4 山东 | +30 / +14 |
| `453c7a90` | B.5 江浙(收官) | +11 / +6 |

---

## 量化(Tier B 单独)

| 指标 | 值 |
|---|---:|
| 入库政策 | **120** |
| 关系边 | **70**(cites 41 + aligns 23 + clarifies 3 + extends 2 + iterates 1) |
| junk drop | 52(27 hard + 25 audit-blocked) |
| LLM cost | ~700K tokens(opus 4.7,10 subagent runs) |
| 时长 | wall ~2 hr(并行 fetch + subagent) |

## P2.7 (Tier A + Tier B) 累计

| 指标 | 起点 | Tier A | Tier B | 当前 |
|---|---:|---:|---:|---:|
| 政策(raw) | 674 | +226 | +120 | **1020** |
| 双向边 | ? | ? | ? | **226** |
| 真孤立 | 132 | +23 | +6 | **161** |
| derives backlog | 4 | +80+ | +30+ | ~110+ |
| LLM cost | 0 | 1.5M | 0.7M | **2.2M tokens** |

---

## 校准 #5 — P0 省 vs 非 P0 省质量对比

| 维度 | Tier A(非 P0 省) | Tier B(P0 省) | 解释 |
|---|---|---|---|
| fetch 成功率 | 75-92%(平均 82%) | 75-96%(平均 87%) | P0 省 portal 稳定性高 |
| hard junk / 批 | 平均 17 | 平均 5 | P0 省 portal 内容更干净 |
| audit_blocked / 批 | 平均 14 | 平均 5 | trafilatura 在 P0 省抓得到 body |
| rel_judge yield / 批 | 30 边 | 14 边 | Tier B 主题(碳/设备更新)vault 邻居稀,缺上位 NDRC 文件 |
| 5C 准确率 | A.1 70% 后修正 | 100% | 校准修复永久受益 |

**关键洞察**:Tier B 入库率虽高于 Tier A(120/242 vs 223/790),但**关系网络密度低**(70 边 vs 184 边)。原因是 Tier B 主题 candidates 的上位 NDRC 文件(成品油市场办法、碳市场总量配额等)很多不在 vault 中。后续 reverse_cites trigger 应配合 missing_base_policies 补抓上位。

---

## 当前 vault 健康指标

```
政策总数:1020
边总:2003(8 类活跃)
4 象限:双向 226 / 仅入向 79 / 仅出向 554 / 真孤立 161
反链页期望覆盖:305
```

孤立从 132 → 161(+29),其中 Tier A 贡献 +23,Tier B 贡献 +6。Tier B 孤立增量小说明 P0 省政策即使 cite 网外,也常被 vault 内政策反向引用。

---

## Pending(下一阶段优先级)

### P0 — 立即(本周)
1. **reverse_cites trigger 跑 161 真孤立** — 派 reverse_cites subagent 找 vault 中政策对这些 isolated 的 inbound 边
2. **derives_from backlog 处理(110+ unresolved)** — 跑 L1.3 demand-pull,priority 排序后批量 fetch missing NDRC 上位文件

### P1 — 中期(本月)
3. **Tier C 启动(341 url long tail)** — **不一次性做**,挂 daily_query
4. **fetch_failed manual queue** — 累计 ~210+ url SSL/TLS 失败,走 SKILL §A.6.3 fallback chain
5. **vault metadata 错配 audit** — Tier A.4 / B.5 多次发现 official_number ↔ title 不匹配,扫一次性脚本

### P2 — 长期
6. **opinions-summary 重生**(commentary stance 跨 191 篇过期阈值后)
7. **Tier B 中信用 list 页 / 油价通知 series 二次清理**(B.2 上海发现 ~5 个低价值聚合页可补 drop)

---

## 启动 Tier C 时(异步 daily_query)

```bash
# Tier C 不一次性大批跑,接 daily_query 自然消化:
cat _meta/audit/p2_7_remaining/tier_c_long_tail.jsonl >> _meta/queue/daily_pending.jsonl

# 让 daily_query 周期跑(已配置 launchd):
ls _meta/launchd/  # com.shaoziyuan.policy-vault-daily-query.plist
```

---

## 关联文件

- `_meta/audit/p2_7_remaining/tier_c_long_tail.jsonl` — Tier C 立项(未做)
- `_meta/audit/p2_7_remaining/b{1..5}_*.jsonl` — Tier B 切批 jsonl(本会话产出)
- `_meta/scripts/oneshot_split_tier_b_by_province.py` — Tier B 切批模板
- `docs/handoffs/2026-05-08-tier-a-completion-handoff.md` — Tier A 完结 handoff
- SKILL §A.6.8 — P2.7 切批 SOP(已落 Tier A 经验)
- SKILL §6.1 / §8d / §8e — vault 派生层契约
