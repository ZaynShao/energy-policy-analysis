---
title: P2.7 剩余候选(扣除 p0_refetch_seeds R3 已立项)
generated_at: 2026-05-07T17:08:32+08:00
generated_by: _meta/scripts/oneshot_build_p2_7_remaining.py
total_remaining: 1373
p0_x_p0_already_in_p0_refetch_seeds: 323
---

# P2.7 剩余候选 — 分层立项

**总**: 1373 url
(扣除已在 `_meta/audit/p0_refetch_seeds.md` R3 中的 P0 主题×P0 省 323 url 后)

## 分层概览

| Tier | 描述 | 数量 | 文件 | 优先级 |
|---|---|---:|---|---|
| **A** | P0 主题 × 非 P0 省 / national | 790 | `tier_a_p0_theme_other_prov.jsonl` | **高**(P0 内容,跨省补全) |
| **B** | 非 P0 主题 × P0 省 | 242 | `tier_b_other_theme_p0_prov.jsonl` | 中(京沪苏浙鲁粤的碳市场/设备更新等) |
| **C** | 非 P0 主题 × 非 P0 省 | 341 | `tier_c_long_tail.jsonl` | 低(长尾) |

## Tier A 主题分布(790 P0 主题候选,跨非 P0 省)

| theme | 候选数 |
|---|---:|
| 新型储能 | 141 |
| 电力市场 | 122 |
| 充电基础设施 | 121 |
| 配电网开放 | 118 |
| V2G | 106 |
| 虚拟电厂 | 102 |
| 聚合商接入 | 60 |
| 绿电交易 | 15 |
| 居住充电 | 3 |
| 设备更新 | 2 |

## Tier B 省份分布(242 非 P0 主题在 P0 省)

| province | 候选数 |
|---|---:|
| 广东 | 54 |
| 上海 | 51 |
| 北京 | 51 |
| 山东 | 50 |
| 江苏 | 23 |
| 浙江 | 13 |

## 执行建议

1. **先做 p0_refetch_seeds R3 / R2**(已立项,323 url,P0×P0,见独立文件)
2. **再做 Tier A**(790)— 分批 fetch + trigger A:
   ```bash
   python3 _meta/audit_2026-05-06/fetch_candidates.py \
     --in _meta/audit/p2_7_remaining/tier_a_p0_theme_other_prov.jsonl \
     --log _meta/audit_2026-05-06/fetch_p2_7_a.log \
     --concurrency 8
   # → normalize_to_raw + trigger A.1 prepare 派 5C / rel_judge subagent
   ```
   按主题切批(每主题 ~100-140 url),每批走完整 trigger A 流程
   (~1-2 小时 LLM)
3. **Tier B**(242)— 同上,按省切批
4. **Tier C**(341)— 长尾,可走 daily_query 自动重抓而非一次性

## 关联文件

- `_meta/audit/p0_refetch_seeds.md` — P0×P0 优先,323 url(本清单不重复)
- `_meta/audit/missing_base_policies.md` — 53 base pid commentary 引用断
- `_meta/audit/p0_gaps_diagnosis.md` — R0-R4 漏抓机制诊断
- SKILL §A.6 — P0 漏抓诊断 + 重抓协议
