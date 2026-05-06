#!/usr/bin/env python3
"""
gen_march_dryrun.py
生成 3 月月报 dry-run markdown,落到 ~/Desktop。
不调用 LLM,只用现成数据 + 占位标记。让用户拍板结构。
"""

import re
import json
import yaml
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date, datetime

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
DESKTOP = Path.home() / "Desktop"
OUT = DESKTOP / "能源政策月报-2026-03-DRYRUN.md"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def main():
    # 加载所有政策
    all_p = {}
    for f in (VAULT / "0_raw" / "policies").glob("*.md"):
        text = f.read_text(encoding="utf-8")
        fm, body = parse_fm(text)
        if fm is None or not fm.get("id"):
            continue
        all_p[fm["id"]] = {"fm": fm, "body": body, "filename": f.name}

    # 3 月政策
    march = [(pid, m) for pid, m in all_p.items()
             if str(m["fm"].get("date") or "").startswith("2026-03")]
    march.sort(key=lambda x: (-x[1]["fm"].get("重要性", 0), x[1]["fm"].get("date", "")))

    # 业务关键词归类
    biz_strong = ["V2G", "车网", "虚拟电厂", "充电基础设施", "充电桩", "充换电",
                  "电力市场", "电力交易", "辅助服务", "现货市场",
                  "储能", "新型储能", "需求响应",
                  "加油", "成品油", "综合能源",
                  "新能源汽车", "以旧换新", "设备更新"]

    def relevance(p):
        title = p["fm"].get("title", "")
        tags = " ".join(str(t) for t in (p["fm"].get("tags") or []))
        full = title + " " + tags
        matched = [k for k in biz_strong if k in full]
        return matched

    strong = []  # 重要性 ≥4 + biz 词命中
    medium = []  # 重要性 3 + biz 词命中
    weak = []    # 弱相关
    for pid, m in march:
        imp = m["fm"].get("重要性", 0) or 0
        kws = relevance(m)
        if imp >= 4 and kws:
            strong.append((pid, m, kws))
        elif imp == 3 and kws:
            medium.append((pid, m, kws))
        else:
            weak.append((pid, m, kws))

    # 月度对比
    month_dist = Counter()
    month_imp = defaultdict(list)
    for pid, m in all_p.items():
        d = str(m["fm"].get("date") or "")
        if len(d) >= 7:
            month_dist[d[:7]] += 1
            month_imp[d[:7]].append(m["fm"].get("重要性", 0) or 0)

    # entity 链接(用于显示主题归属)
    policy_entities = defaultdict(set)
    with open(VAULT / "1_extracted" / "entities" / "_extractions.jsonl") as f:
        for line in f:
            d = json.loads(line)
            policy_entities[d["policy_id"]].add(d["canonical_id"])

    # 3 月政策涉及关系
    march_pids = set(pid for pid, _ in march)
    march_relations = []
    for rel in ["supersedes", "references", "clarifies", "iterates", "extends", "aligns_with"]:
        rp = VAULT / "1_extracted" / "relations" / f"{rel}.jsonl"
        if not rp.exists():
            continue
        for line in open(rp):
            d = json.loads(line)
            if d.get("from") in march_pids or d.get("to") in march_pids:
                march_relations.append({"rel": rel, **d})

    # ≥4 全 vault
    ge4 = [(pid, m) for pid, m in all_p.items()
           if (m["fm"].get("重要性", 0) or 0) >= 4]

    # 3 月 ≥4 是否有 opinions
    op_dir = VAULT / "1_extracted" / "opinions"
    march_with_opinions = [pid for pid in march_pids if (op_dir / f"_op_{pid}.md").exists()]

    # 主题 → 31 省覆盖
    PROV = {"北京市", "天津市", "上海市", "重庆市", "河北省", "山西省", "内蒙古自治区",
            "辽宁省", "吉林省", "黑龙江省", "江苏省", "浙江省", "安徽省", "福建省",
            "江西省", "山东省", "河南省", "湖北省", "湖南省", "广东省",
            "广西壮族自治区", "海南省", "四川省", "贵州省", "云南省", "西藏自治区",
            "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区"}
    theme_coverage = {}
    for theme_id, theme_zh in [("v2g", "V2G"), ("power_market", "电力市场"),
                                ("charging_infra", "充电基建"), ("new_ess", "新型储能"),
                                ("equipment_renewal", "设备更新")]:
        covered = set()
        for pid in policy_entities:
            if pid not in all_p:
                continue
            if theme_id in policy_entities[pid]:
                r = all_p[pid]["fm"].get("region") or {}
                if r.get("level") == "省" and r.get("name") in PROV:
                    covered.add(r["name"])
        blank = PROV - covered
        theme_coverage[theme_zh] = (covered, blank)

    # ============== 渲染 markdown ==============
    L = []

    L.append("# 能源政策月报 — 2026 年 3 月")
    L.append("")
    L.append(f"_DRY-RUN PREVIEW · 生成于 {datetime.now().isoformat(timespec='seconds')} · 0 LLM 调用_")
    L.append("")
    L.append("> **此文件用途**:让用户先看月报骨架 + 现成数据样本,**确认结构后**再启动 LLM 抽取(124 政策 effective/expires + 8 政策业务影响详读)+ matplotlib 图表 + docx 渲染。")
    L.append("")
    L.append("> **章节标记说明**:")
    L.append("> - 🟢 数据已就位,可直接渲染")
    L.append("> - 🟡 现有数据 + 部分需 LLM 增强")
    L.append("> - 🔴 完全靠 LLM 输出(标 PLACEHOLDER)")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 目录(章节 + 字数 + 数据状态)")
    L.append("")
    L.append("| § | 章节 | 字数估 | 数据状态 | 主要数据源 |")
    L.append("|:-:|------|:----:|:----:|------|")
    L.append("| 0 | 封面 + 目录 | - | 🟢 | 模板 |")
    L.append("| 1 | 月度速览 | 600 | 🟡 | 月度对比 + 数字一览(已查) |")
    L.append("| 2 | 红绿灯决策卡片(6 重要政策) | 1200 | 🔴 | 业务影响需 LLM |")
    L.append("| 3 | 政策全列表(8 篇分 3 档) | 1500 | 🟡 | 强相关需 LLM 摘要,弱相关 1 行带过 |")
    L.append("| 4 | 重点解读(2-3 篇深度) | 2000 | 🔴 | 政策介绍 + 业务影响 + 行动建议 |")
    L.append("| 5 | 跨月演进脉络(国家→省→县) | 800 | 🟢 | relations 数据(2 条 + 历史扩展) |")
    L.append("| 6 | 舆论温度计 | 600 | 🟡 | **3 月 0 opinions**,改用历史同主题作背景 |")
    L.append("| 7 | 机会-风险 2x2 矩阵 | 400 + 图 | 🟡 | 现有 frontmatter 数据 + Python 计算 |")
    L.append("| 8 | 缺口/盲区警示 | 600 | 🟢 | 主题 × 省份覆盖矩阵(已查) |")
    L.append("| 9 | 下月 watching list | 400 | 🟡 | 已知政策窗口期 + LLM 推断 |")
    L.append("| 10 | 数据健康度小卡 | 200 | 🟢 | weekly lint 报告 |")
    L.append("| A | 附录 A:生效周期图(timeline) | 图 1 张 | 🔴 | LLM 抽 124 政策 effective/expires |")
    L.append("| B | 附录 B:重要政策各省覆盖度 | 图 + 表 | 🟢 | 主题 × 31 省矩阵 |")
    L.append("| C | 数据出处与方法论 | 200 | 🟢 | 描述 L1+L2 流程 |")
    L.append("")
    L.append(f"**总字数估**:约 8,500 + 4-6 张图,**约 30-40 页 docx**")
    L.append("")
    L.append("---")
    L.append("")

    # ============== § 1 月度速览 ==============
    L.append("## § 1 月度速览(🟡)")
    L.append("")
    L.append("### 数字一览")
    L.append("")
    L.append("| 指标 | 本月(3 月) | 上月(2 月) | 上上月(1 月) |")
    L.append("|------|:----:|:----:|:----:|")
    L.append(f"| 入库政策数 | **{month_dist.get('2026-03', 0)}** | {month_dist.get('2026-02', 0)} | {month_dist.get('2026-01', 0)} |")
    feb_imp = sum(1 for i in month_imp.get('2026-02', []) if i >= 4)
    jan_imp = sum(1 for i in month_imp.get('2026-01', []) if i >= 4)
    mar_imp = sum(1 for i in month_imp.get('2026-03', []) if i >= 4)
    L.append(f"| 重要政策(⭐≥4) | **{mar_imp}** | {feb_imp} | {jan_imp} |")
    L.append(f"| 强业务相关 | **{len(strong)}** | (待计算) | (待计算) |")
    L.append("")
    L.append("### 本月最重要 1-2 件事(LLM 校准)")
    L.append("")
    L.append('🔴 **PLACEHOLDER**:Agent 看完 6 篇重要政策后产出 1-2 句「本月最值得决策层关注」。')
    L.append("")
    L.append(f"**初步判断**(基于 frontmatter):")
    L.append(f"- ⭐ 山东省虚拟电厂高质量发展方案(2026-03-27)— **省级 VPP 准入门槛 + 容量电价**,是 NDRC 357 国家级 VPP 指导意见后**首批省级落地**之一")
    L.append(f"- ⭐ 宁夏回族自治区 2026 年度充电基础设施建设实施方案(2026-03-20)— **西北 5/5 空白省份首破**,信号意义大于补贴量")
    L.append("")

    # ============== § 2 红绿灯决策卡片 ==============
    L.append("## § 2 红绿灯决策卡片(🔴 LLM 必填业务影响)")
    L.append("")
    L.append("> 6 张卡片,**每张 ~150 字**。Agent 工作量:6 × 1 LLM 调用读全文 + 输出。")
    L.append("")
    L.append("### 样本(Agent 输出后形态参考)")
    L.append("")
    if strong:
        p = strong[0]
        L.append(f"```")
        L.append(f"🔴 立即行动                          {p[0]}")
        L.append(f"")
        L.append(f"📜 政策   {p[1]['fm'].get('title','')[:50]}")
        L.append(f"          {p[1]['fm'].get('official_number','') or '(无文号)'}")
        L.append(f"📅 发布   {p[1]['fm'].get('date','')}  ·  发文:{'/'.join(p[1]['fm'].get('issuer',[]))[:35]}")
        L.append(f"⭐ 评分   D1×0.4 + D2×0.4 + D3×0.2 = {p[1]['fm'].get('重要性')}")
        L.append(f"🏷️  标签  {p[2]}")
        L.append(f"")
        L.append(f"💡 一句政策核心  PLACEHOLDER (LLM 写)")
        L.append(f"🎯 一句滴滴影响  PLACEHOLDER (LLM 写)")
        L.append(f"🚀 行动建议      PLACEHOLDER (LLM 写,≥1 条具体动作)")
        L.append(f"🔗 详读路径      vault://0_raw/policies/{p[1]['filename']}")
        L.append(f"```")
        L.append("")
    L.append(f"**6 张卡片对应政策**(强 2 + 中 4):")
    for pid, m, kws in strong + medium:
        L.append(f"- {'🔴' if m['fm'].get('重要性') >= 4 else '🟡'} `{pid}` — {m['fm'].get('title','')[:40]}")
    L.append("")

    # ============== § 3 政策全列表 ==============
    L.append("## § 3 政策全列表(🟡 强相关需 LLM 摘要)")
    L.append("")
    L.append(f"### 3.1 强相关 ⭐≥4 + 业务命中({len(strong)} 篇,每篇 200-300 字详写)")
    L.append("")
    for pid, m, kws in strong:
        fm = m["fm"]
        L.append(f"#### {fm.get('title','')[:60]}")
        L.append(f"")
        L.append(f"- **id**: `{pid}`  ·  **文号**: {fm.get('official_number') or '(无)'}")
        L.append(f"- **发布**: {fm.get('date')}  ·  **机构**: {' / '.join(fm.get('issuer', []))}")
        L.append(f"- **区域**: {fm.get('region', {}).get('name','')}  ·  **重要性**: {fm.get('重要性')}⭐  ·  **行动**: {fm.get('行动分类','')}")
        L.append(f"- **业务标签命中**: {kws}")
        L.append(f"- **价值标签**: {fm.get('价值标签', [])}")
        L.append(f"- **政策摘要**:🔴 PLACEHOLDER (LLM 读全文产出 ~80 字)")
        L.append(f"- **业务影响**:🔴 PLACEHOLDER (LLM 分加油/充电/电力三段)")
        L.append(f"- **行动建议**:🔴 PLACEHOLDER (LLM 1-3 条)")
        L.append("")

    L.append(f"### 3.2 中相关 ⭐3 + 业务命中({len(medium)} 篇,每篇 ~80 字)")
    L.append("")
    for pid, m, kws in medium:
        fm = m["fm"]
        L.append(f"- **{fm.get('title','')[:50]}** `{pid}`")
        L.append(f"  - {fm.get('date')} · {fm.get('region',{}).get('name','')} · ⭐{fm.get('重要性')} · 命中:{kws}")
        L.append(f"  - 简述:🟡 PLACEHOLDER (~50 字)")
    L.append("")

    L.append(f"### 3.3 弱相关或非业务({len(weak)} 篇,每篇 1 行)")
    L.append("")
    for pid, m, kws in weak:
        fm = m["fm"]
        L.append(f"- {fm.get('date')} `{pid}` {fm.get('title','')[:40]}(⭐{fm.get('重要性')},{'已业务命中' if kws else '业务无关'})")
    L.append("")

    # ============== § 4 重点解读 ==============
    L.append("## § 4 重点解读(🔴 2-3 篇深度,每篇 600-900 字)")
    L.append("")
    L.append("### 候选 Top 3(待用户确认)")
    L.append("")
    L.append("**Agent 推荐选这 3 篇深度展开**:")
    L.append("")
    L.append(f"1. **山东省虚拟电厂高质量发展方案** (`P_2026_SD_03271ffc`)")
    L.append(f"   - 理由:NDRC 357 后首批省级落地,VPP 资质 / 容量电价 / 调度规则一手参考")
    L.append(f"   - 现有材料:relations[references → P_2025_NDRC_357_a]")
    L.append("")
    L.append(f"2. **宁夏 2026 年度充电基础设施建设实施方案** (`P_2026_NX_0320e07e`)")
    L.append(f"   - 理由:西北 5/5 空白首破")
    L.append(f"   - ⚠️ 已知问题:body 仅 0.99KB(weekly lint flag),解读会偏空")
    L.append("")
    L.append(f"3. **2026 年能源行业标准计划立项指南** (`P_2026_NEA_0324cd2a`)")
    L.append(f"   - 理由:虚拟电厂 / 充电桩 / 储能国家标准前瞻信号")
    L.append("")

    # ============== § 5 跨月演进 ==============
    L.append("## § 5 跨月演进脉络(🟢 关系网现成)")
    L.append("")
    L.append(f"### 3 月政策涉及的关系链 ({len(march_relations)} 条)")
    L.append("")
    for r in march_relations:
        from_t = all_p.get(r["from"], {}).get("fm", {}).get("title", "?")[:30]
        to_t = all_p.get(r["to"], {}).get("fm", {}).get("title", "?")[:30]
        L.append(f"- **[{r['rel']}]** `{r['from']}` ({from_t}) → `{r['to']}` ({to_t})")
        if r.get("evidence"):
            L.append(f"  - {r['evidence'][:80]}")
    L.append("")
    L.append("### 推断的「国家→省→县」演进图(配 PNG)")
    L.append("")
    L.append("```")
    L.append("国家级               省级                 地市/区级")
    L.append("─────────            ──────────           ─────────")
    L.append("NDRC 357 (2025-04) ──→ 山东 VPP方案(本月)  ─→ ?")
    L.append("                       ↗")
    L.append("NDRC 1656 (2025-12)─┘  福建/上海/广东等 (1656 实施细则备案)")
    L.append("")
    L.append("NDRC 1015 三年倍增 ──→ 宁夏充电方案(本月) ─→ ?")
    L.append("    (2025-10)            (西北 5/5 首破)")
    L.append("")
    L.append("国办 19 充电指导    ──→ 北京/上海/广东/重庆 (历史扩展)")
    L.append("    (2023)             (本月地市级动作较少)")
    L.append("```")
    L.append("")

    # ============== § 6 舆论温度计 ==============
    L.append("## § 6 舆论温度计(🟡 数据稀缺,要降级处理)")
    L.append("")
    L.append(f"### ⚠️ 数据现实")
    L.append(f"- 3 月 8 政策中,**有 opinions 的: {len(march_with_opinions)}**(0)")
    L.append(f"- 原因:评论需 1-2 月发酵,3 月新政评论尚未抓回")
    L.append("")
    L.append(f"### 替代方案(降级)")
    L.append(f"- A. **同主题历史舆论展示**:展示电力市场 + V2G + 充电基建主题的 30 天滚动 stance 分布(用现成 54 个 opinions)")
    L.append(f"- B. **本月政策舆论缺位声明**:正文一行说明,留空")
    L.append(f"- C. **快速搜补**:Step 6 重跑(L1 用 Tavily 搜本月政策评论)— 工作量约 30 分钟,LLM 抽 stance 另需 30 分钟")
    L.append("")
    L.append(f"**推荐:A**(展示同主题历史舆论作背景)")
    L.append("")

    # ============== § 7 机会-风险 2x2 ==============
    L.append("## § 7 机会-风险 2x2 矩阵(🟡 配 PNG 图)")
    L.append("")
    L.append("```")
    L.append("                立即行动        中期跟踪")
    L.append("            ┌────────────────┬────────────────┐")
    L.append("  强相关    │  山东 VPP      │                │")
    L.append("  ⭐≥4    │  宁夏充电      │                │")
    L.append("            ├────────────────┼────────────────┤")
    L.append("  中相关    │ 能源标准计划   │ 松江能源行动   │")
    L.append("  ⭐3      │                │ 重庆重点项目   │")
    L.append("            │                │ 丰台美丽建设   │")
    L.append("            └────────────────┴────────────────┘")
    L.append("")
    L.append("(弱相关 2 篇不入矩阵)")
    L.append("```")
    L.append("")

    # ============== § 8 缺口/盲区 ==============
    L.append("## § 8 缺口 / 盲区警示(🟢 现成数据)")
    L.append("")
    L.append("### 主题 × 省份覆盖矩阵")
    L.append("")
    L.append("| 主题 | 已覆盖 | 31 省覆盖率 | 关键空白(滴滴重点市场) |")
    L.append("|------|:----:|:----:|------|")
    for theme_zh, (covered, blank) in theme_coverage.items():
        important_blanks = [p for p in ["广东省", "江苏省", "浙江省", "山东省", "上海市"] if p in blank]
        L.append(f"| {theme_zh} | {len(covered)}/31 | {len(covered)/31*100:.0f}% | {' / '.join(important_blanks) if important_blanks else '已覆盖'} |")
    L.append("")
    L.append("### 本月新填空白")
    L.append("- ✅ 充电基建:**宁夏首破**(西北 5/5 空白省份之一)")
    L.append("- ✅ 电力市场:山东 VPP 方案(电力市场覆盖加深)")
    L.append("")
    L.append("### 持续盲区(1 个月警告)")
    L.append("🔴 PLACEHOLDER (LLM 跨主题 + 滴滴优先省份判断 — 但可半自动)")
    L.append("")

    # ============== § 9 下月 watching list ==============
    L.append("## § 9 下月 watching list(🟡 已知窗口 + LLM 推断)")
    L.append("")
    L.append("### 已知政策窗口期(基于关系网)")
    L.append(f"- **NDRC 1656 各省实施细则备案**:截止 2026-03-01 已过,各省 4 月跟踪窗口 — 江苏 / 浙江 / 广东 0 政策待发布")
    L.append(f"- **V2G 9 城试点扩围(第二批)**:2026 Q2 决策预期")
    L.append(f"- **充电统建统服 1000 个名额申报**:Q2 申报开放(NDRC 101520b2)")
    L.append("")
    L.append("### LLM 增量推断")
    L.append(f"🔴 PLACEHOLDER (Agent 基于历史关系 + 演进规律推断 4 月可能出台的政策)")
    L.append("")

    # ============== § 10 数据健康度 ==============
    L.append("## § 10 数据健康度小卡(🟢 现成 lint 报告)")
    L.append("")
    L.append("```")
    L.append("vault 现状(2026-04-26):")
    L.append("  - 0_raw/policies:    286 篇(本月新增 8)")
    L.append("  - commentaries:      338 篇")
    L.append("  - 实体 canonical:    88")
    L.append("  - 关系总数:          198")
    L.append("  - 主题结晶页:        3 (V2G / 电力市场 / 充电基建)")
    L.append("")
    L.append("Weekly Lint:")
    L.append("  - errors:   1   (慈溪市能源规划缺 date)")
    L.append("  - warnings: 34  (低质量采集,L1 重抓清单)")
    L.append("  - infos:    3")
    L.append("```")
    L.append("")

    # ============== 附录 A ==============
    L.append("## 附录 A:重要政策生效周期(🔴 LLM 抽 124 篇)")
    L.append("")
    L.append("### 数据准备(LLM 工作)")
    L.append(f"- 候选范围:全 vault ⭐≥4 政策共 **{len(ge4)} 篇**")
    L.append(f"- 每篇抽:`effective_date` / `expires_at` / `source_quote`")
    L.append(f"- 报告日 2026-03-31 视角过滤:**effective ≤ 2026-03-31 且 (expires ≥ 2026-03-31 或 null)**")
    L.append(f"- 预计渲染政策数:30-50 篇")
    L.append("")
    L.append("### 渲染样式(matplotlib 横向 Gantt)")
    L.append("```")
    L.append("                           |----- 2024 -----|----- 2025 -----|----- 2026 -----|")
    L.append("国发〔2024〕12 节能降碳   ████████████████████████████████████░░░░░░░░░░░░░░")
    L.append("                          生效 2024-05-23                有效期 ~2025-12-31")
    L.append("发改能源规〔2025〕1656   ░░░░░░░░░░░░░░░░░░░░░░░░░░██▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
    L.append("                                                  施行 2026-03-01 长期")
    L.append("...")
    L.append("```")
    L.append("")

    # ============== 附录 B ==============
    L.append("## 附录 B:重要政策各省覆盖度(🟢 现成数据)")
    L.append("")
    L.append("### B1. 主题 × 省份覆盖热力图(配 PNG)")
    L.append("")
    L.append("```")
    L.append("              V2G  电力市场  充电基建  储能  设备更新")
    L.append("北京市         ✅    ✅       ✅       ✅    ✅")
    L.append("上海市         ✅    ✅       ✅       ✅    ✅")
    L.append("广东省         ✅    ❌       ✅       ❌    ✅")
    L.append("...")
    L.append("(31 行 × 5 列,空白用色块标记)")
    L.append("```")
    L.append("")
    L.append("### B2. 本月新政在 31 省的扩散预期")
    L.append("- 山东 VPP → 预计跟随省份:广东 / 江苏 / 浙江(经济发达 + 电力交易市场成熟)")
    L.append("- 宁夏充电 → 预计跟随省份:陕西 / 甘肃 / 青海(西北邻省)")
    L.append("")

    # ============== 附录 C ==============
    L.append("## 附录 C:数据出处与方法论")
    L.append("")
    L.append("### 数据来源")
    L.append(f"- **L1 采集**:`policy-watch` skill(8 步采集法 + Step 2.5 渠道回写 + Step 3.5 URL 去重 + Step 4.5 结构化抽取)")
    L.append(f"- **L2 派生**:9 个脚本(`_meta/scripts/`)+ Karpathy LLM Wiki v2 schema")
    L.append(f"- **打分体系**:六维(D1 业务 / D2 影响 / D3 层级 / D4 紧迫 / D5 实操 / D6 窗口)")
    L.append("")
    L.append("### 局限说明")
    L.append(f"- 本月评论数据稀缺(政策需 1-2 月发酵)")
    L.append(f"- 124 ≥4 政策中 ~13% 是低质量采集(weekly lint 已 flag,L1 step4 改进点)")
    L.append("")

    # ============== 写文件 ==============
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"\n=== Dry-run markdown saved ===")
    print(f"  {OUT}")
    print(f"  size: {OUT.stat().st_size} bytes")
    print(f"  lines: {len(L)}")


if __name__ == "__main__":
    main()
