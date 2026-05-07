---
title: 2026-05-07 P0 Refetch handoff — 主 session 接收
date: 2026-05-07
prev_commits:
  - 18af20c7 feat(P0 refetch L2/L3)
  - ce4507f8 feat(P0 refetch L1)
  - c28e7ac6 chore(P2.7 立项)  # 起点
target: 主 session
priority: P0
status: 已落地,留 follow-up
estimated_followup_time: 30-60 min(看是否做 manual queue 浏览器抓 + dedup 决策)
---

# Handoff:P0 主题×P0 省 refetch — 落地完成 + 5 项跟进

按 SKILL §A.6.7 + `_meta/audit/p0_refetch_seeds.md`(R2 7 + R3 56 url)
执行完整 trigger A 流程。**10 实政策入 vault,12 关系边,9 主题刷新**。
2 commit 已上 main:`ce4507f8`(L1 raw)+ `18af20c7`(L2/L3 派生)。

---

## 0. 已完成 — 不要重做

| 阶段 | 动作 | 数量 | 落点 |
|---|---|---|---|
| Phase 0a | fetch_candidates.py 抓 R2+R3 unique 46 url | 32 OK / 14 fail | `0_raw/policies_staging_2026-05-06/` |
| Phase 0b | playwright + Clash proxy 试 SSL fallback | 0/10 通(jsdsm 端口 10443 网络层卡死) | manual queue |
| Phase 0c | normalize_to_raw 入 raw + dedup | 26 入 / 6 dup | `0_raw/policies/` |
| Phase 0d | 二次质量过滤(news/答复/综述/dupe) | 16 archived | `0_raw/_archive/policies/p0_refetch_drops_2026-05-07/` |
| Phase 0e | 70875d73 fm 修补(date/issuer/region) | 1 fix | raw fm |
| Phase 1a | trigger A prepare(audit pass) | 10 pid stage | `_l2_rebuild_state/{5c,rel_judge}/` |
| Phase 1b | 派 5C subagent (opus 4.7) | 10/10 results | `_l2_rebuild_state/5c/results/results.jsonl` |
| Phase 1c | 派 rel_judge subagent (opus 4.7) | 12 边 / 7 target hit | `_l2_rebuild_state/rel_judge/results/results.jsonl` |
| Phase 1d | apply --stage 5c | 10 yaml + 8 derives + 4 unresolved → backlog | `_meta/business_view/`,`backlog/` |
| Phase 1e | apply --stage rel | +9 cites_basis / +1 iterates / +2 aligns_with | `1_extracted/relations/*.jsonl` |
| Phase 1f | deterministic post-llm | 9 主题 + regions + global + reverse_links | `2_crystallized/` + `_index_by_policy/` |

---

## 1. 入库 10 政策清单

| pid | 标题 | 关键文号 | 关系象限 |
|---|---|---|---|
| `P_2022_GO_0ae1a2cc` | 江苏省"十四五"新型储能发展实施方案(wnd 镜像) | — | outbound_only |
| `P_2023_GO_93548e55` | 江苏省"十四五"新型储能发展实施方案(wxlx 镜像) | — | outbound_only |
| `P_2024_GO_378cdbce` | **深圳市支持虚拟电厂加快发展的若干措施** | 深发改规〔2024〕4号 | bidirectional ⭐ |
| `P_2025_GO_39a47213` | 国家能源局首批 V2G 试点公告(9 城 30 项目) | — | outbound_only |
| `P_1900_GO_70875d73` | 广州市工信委 2017 充电桩(已被 2019 取代) | 穗工信规字〔2017〕2号 | bidirectional |
| `P_2019_GO_781f09c6` | 广州市工信局 2019 充电桩(iterates 2017) | 穗工信规字〔2019〕1号 | bidirectional |
| `P_2019_GO_0c52cbb8` | 广州海珠区 2019-2021 充电桩补贴申报 | — | outbound_only |
| `P_2018_GO_3e8388c2` | 广州市充电基础设施补贴资金管理办法 | 穗工信规字〔2018〕3号 | outbound_only |
| `P_2022_GO_68e2ddd3` | 南京居民区充电桩管理办法 | — | **isolated** ⚠ |
| `P_2025_GO_0f4d0834` | 广州白云区 V2G 标杆示范遴选 | — | **isolated** ⚠ |

亮点关系:
- 江苏储能两版各 cites 国家级 1051(指导意见)/209(十四五方案)/475(参与电力市场)三件套(6 边)
- 广州充电桩 2019 → 2017 iterates(2017 显式作废)+ 都 cites 国办〔2015〕73号
- 深圳虚拟电厂(深发改规〔2024〕4号)→ aligns_with 同名「措施正文」(避免 supersedes)
- V2G 试点公告(39a47213)→ aligns_with 718 号试点工作通知

---

## 2. 留给主 session 的 5 项跟进

### #1 Manual queue 14 url(P1,看是否补)

`_meta/audit/p0_refetch_manual_queue.jsonl`:

| 类别 | 数 | 处置建议 |
|---|---|---|
| jsdsm.fzggw.jiangsu.gov.cn:10443 | 10 | LibreSSL 2.8.3 + playwright/chromium + Clash 三层都打不通,**直连超时,Clash 转发 ERR_CONNECTION_CLOSED**。要么浏览器手抓 → `_meta/audit_2026-05-06/manual_staging/<8hash>.md` → normalize → trigger A;要么换 ndrc/nea 镜像源(SKILL §A.6.3 fallback 4) |
| nea.gov.cn `.doc` | 1 | 老二进制乱码,可 `textutil -convert html` 转换 → 重抓 |
| gov PDF 空(suzhou + changzhou) | 2 | scan 件,需 OCR(`tesseract` / Adobe) |
| zjj.sz answer 38B | 1 | 真无内容,直接跳过 |

**注意**:9/10 jsdsm jhtml 是新闻/年鉴/解读(年鉴《电网篇》、新闻发布会实录),
不是真政策;只 1 个 PDF(售电公司监管实施办法)是实政策。建议只对 PDF 走 fallback,
其余跳过。

### #2 Backlog 4 条 demand-pull(P0,下轮 L1.3 一起补)

`_meta/backlog/derives_from_unresolved.yaml`:

- `粤发改能电〔2016〕691号` 广东省电动汽车充电基础设施建设运营管理办法
- `粤发改产业函〔2018〕518号` 广东省新能源汽车推广应用地方财政补贴
- `苏工信规〔2022〕2号` 江苏省新能源汽车充(换)电设施建设运营管理办法
- `宁产业链办〔2022〕1号` 南京产业链办相关文(待查)

修了这 4 条,2 个 isolated 新政策(68e2ddd3 / 0f4d0834)会自动转 outbound_only。

### #3 江苏储能两版 dedup 决策(P2,看你)

`P_2022_GO_0ae1a2cc`(wnd.gov.cn 镜像)+ `P_2023_GO_93548e55`(wxlx.gov.cn 镜像)
内容几乎一致(都是江苏省"十四五"新型储能方案)。两版各 cites 国家级 3 件套
(共 6 边,数据冗余)。可选:
- a) 跑 `dedup_policies.py` 选主版本,另一版迁 `_duplicates/`
- b) 当作"双源验证"留着(两个不同省级网站都有副本,作可信度证据)
- c) 不动,信号已落地,后续用户视觉看 graph 不影响

### #4 dropped 16 篇可逆(P3)

[`0_raw/_archive/policies/p0_refetch_drops_2026-05-07/`](../../0_raw/_archive/policies/p0_refetch_drops_2026-05-07/)
+ audit log [`_meta/audit/p0_refetch_drops_2026-05-07.jsonl`](../../_meta/audit/p0_refetch_drops_2026-05-07.jsonl)。

判断略激进的几个(若你觉得该入):
- `P_2025_GO_39a47213` 国家能源局 V2G 试点公告 — 已纳入(EXPLICIT_KEEP override)
- `P_1900_GO_5b690c57` 喜报(苏发改能源发〔2025〕1198号)— title 是"喜报"但 official_number
  是真文号,可考虑回收
- `P_1900_GO_90af778f` 江苏公示首批六大虚拟电厂 — 公示(公示也是规制行为)

恢复方法:`mv 0_raw/_archive/policies/p0_refetch_drops_2026-05-07/{file}.md 0_raw/policies/`
+ trigger A prepare 单 pid。

### #5 P_1900 日期不准(P3,下轮 body audit)

3 个新 pid 的 fm.date 实际是 1900(normalize 抽不出 → fallback):
- `P_1900_GO_70875d73` — 已修为 2017-04-01(本会话)
- `P_1900_GO_5b690c57` / `P_1900_GO_90af778f` 等(已归档,不在 vault)

后续 normalize_to_raw 改进:`extract_date()` 加多一档"从 official_number 文号
反查 issue_year"(穗工信规字〔YYYY〕N号 → YYYY-01-01 fallback)。

---

## 3. 工具新增

[`_meta/audit_2026-05-06/fetch_via_playwright.py`](../../_meta/audit_2026-05-06/fetch_via_playwright.py) —
playwright/chromium + proxy SSL fallback。本次没通 jsdsm(网络层卡死,非 TLS),
但脚本可重用。用法:

```bash
PLAYWRIGHT_PROXY="http://127.0.0.1:7897" python3 _meta/audit_2026-05-06/fetch_via_playwright.py \
  --failed-log _meta/audit_2026-05-06/fetch_xxx.log \
  --candidates _meta/audit_2026-05-06/candidates_xxx.jsonl \
  --filter-domain target.gov.cn \
  --log _meta/audit_2026-05-06/fetch_playwright.log
```

未来撞到别的老 TLS gov 站(发改委独立子站等)可直接用。

---

## 4. 操作 metadata

- **LLM 调用**:5C subagent 1 × 10 pid + rel_judge subagent 1 × 10 target = ~25K tokens i/o。
  trigger A 标准成本(无超额)。
- **履历追踪**:`_meta/audit/rel_judge_history.jsonl` += 10 行 `trigger_A_pid_change`,
  prompt v3.1,model claude-opus-4-7。
- **dedup**:normalize_to_raw 跳 6 个(url 已存在 vault,符合预期)。
- **filename 截断**:`P_2025_GO_e3e7acdd` 三年倍增行动方案 macOS HFS+ 文件名超长截 6 字符,
  归档时已识别为 vault 内 6066.md 的 dupe,无影响。

---

## 5. 验证起点

```bash
cd "/Users/shaoziyuan/Documents/Zayn Main/政策分析"

# 应见这 2 commit
git log --oneline -3
# 18af20c7 feat(P0 refetch L2/L3): ...
# ce4507f8 feat(P0 refetch L1): ...
# c28e7ac6 chore(P2.7 立项): ...     ← 起点

# 工作树干净
git status --short  # 应为空

# 10 新 pid 都在 vault
for pid in P_2022_GO_0ae1a2cc P_2023_GO_93548e55 P_2024_GO_378cdbce \
           P_2025_GO_39a47213 P_1900_GO_70875d73 P_2019_GO_781f09c6 \
           P_2019_GO_0c52cbb8 P_2018_GO_3e8388c2 P_2022_GO_68e2ddd3 \
           P_2025_GO_0f4d0834; do
  ls 0_raw/policies/ | grep -q "$pid" && echo "✓ $pid" || echo "✗ $pid MISSING"
  ls _meta/business_view/ | grep -q "$pid" && echo "  ✓ yaml" || echo "  ✗ yaml MISSING"
done

# 关系层 12 新边落账
python3 _meta/scripts/relations_coverage_metric.py --json | python3 -c "
import json, sys
m = json.load(sys.stdin)
print('total edges by rel:')
for k, v in m['by_relation'].items():
    print(f'  {k}: {v[\"edges\"]}')
"
# 应见 cites_basis 216, iterates 37, aligns_with 141, derives_from 141
```

---

## 6. 不需要做

- ❌ 不要重抓 manual queue 中 jsdsm 9 个 jhtml(都是新闻/年鉴,不是政策)
- ❌ 不要再跑 trigger A prepare(本批 10 pid 已 apply 完成,履历有标)
- ❌ 不要重新过滤 dropped 16 篇(audit log 完整,要恢复用 #4 步骤)
- ❌ 不要碰 `_l2_rebuild_state/`(本批 staging 已 apply,留作下次 trigger A 起点)

---

## 7. 参考资料

- `_meta/audit/p0_refetch_seeds.md` — 原任务清单
- `_meta/audit/p0_gaps_diagnosis.md` — R0-R4 漏抓机制诊断
- `.claude/skills/policy-vault-l2-rebuild/SKILL.md` — §A.6 漏抓诊断协议 + §2 trigger A 流程
- `_meta/audit/missing_base_policies.md` — 53 base pid 评论引用断,与本批 #2 backlog 关联
