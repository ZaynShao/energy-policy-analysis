#!/usr/bin/env python3
"""
render_march_charts.py
为 3 月月报渲染 6 张 PNG 图。

输出到 _meta/march_report_batches/charts/
"""

import json
import re
import yaml
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter, defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np

# 中文字体(macOS)
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'STHeiti', 'Heiti TC', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
BATCHES = VAULT / "_meta" / "march_report_batches"
CHARTS = BATCHES / "charts"
CHARTS.mkdir(exist_ok=True)
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

REPORT_DATE = date(2026, 3, 31)


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def short_title(t, n=22):
    if not t:
        return "?"
    t = re.sub(r'\s+', ' ', t.strip())
    return t[:n] + ("..." if len(t) > n else "")


# 加载 consolidated 数据
with open(BATCHES / "_consolidated.json", encoding='utf-8') as f:
    cdata = json.load(f)
eff_data = cdata['effective_data']
march_detail = cdata['march_detail']

# 加载政策 frontmatter
all_p = {}
for f in (VAULT / "0_raw" / "policies").glob("*.md"):
    text = f.read_text(encoding='utf-8')
    fm = parse_fm(text)
    if fm and fm.get('id'):
        all_p[fm['id']] = fm


def to_date(s):
    if not s: return None
    try:
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except:
        return None


# ============================================================
# 图 1:生效周期 Timeline(横向 Gantt)
# 筛选:国家级 ≥4 仍生效 + 国家级 ≥4 已失效(标红警示) + 本月 march ≥4
# ============================================================
def chart_timeline():
    items = []
    today = REPORT_DATE
    # 国家级 ≥4
    for pid, fm in all_p.items():
        imp = fm.get('重要性', 0) or 0
        if imp < 4: continue
        region_lvl = (fm.get('region') or {}).get('level', '')
        if region_lvl != '国家': continue
        e = eff_data.get(pid)
        if not e or not e.get('effective_date'): continue
        eff = to_date(e['effective_date'])
        exp = to_date(e['expires_at'])
        if not eff: continue
        # 状态分类
        if exp and exp < today:
            status = 'expired'  # 已失效
        elif eff > today:
            status = 'future'   # 未生效
        else:
            status = 'in_force'
        items.append({
            'pid': pid,
            'title': fm.get('title', ''),
            'eff': eff,
            'exp': exp,
            'imp': imp,
            'status': status,
            'official': fm.get('official_number', '') or '',
        })
    # 也加本月 march ≥4 省级
    for pid, fm in all_p.items():
        if pid in [i['pid'] for i in items]: continue
        imp = fm.get('重要性', 0) or 0
        if imp < 4: continue
        d = str(fm.get('date', ''))
        if not d.startswith('2026-03'): continue
        e = eff_data.get(pid)
        if not e or not e.get('effective_date'): continue
        eff = to_date(e['effective_date'])
        exp = to_date(e['expires_at'])
        if not eff: continue
        items.append({
            'pid': pid,
            'title': fm.get('title', ''),
            'eff': eff,
            'exp': exp,
            'imp': imp,
            'status': 'in_force' if (not exp or exp >= today) else 'expired',
            'official': fm.get('official_number', '') or '',
        })

    # 按 effective 排序
    items.sort(key=lambda x: (x['eff'] or date(1900,1,1)))

    # 限制条数(图过密看不清)— 取最近 + 重要性 ≥5 全保 + 本月新政
    important = [i for i in items if i['imp'] >= 5 or (i['eff'] and i['eff'] >= date(2025, 1, 1))]
    if len(important) > 35:
        important = sorted(important, key=lambda x: (-x['imp'], x['eff']))[:35]
    important.sort(key=lambda x: x['eff'])

    # 画图
    fig, ax = plt.subplots(figsize=(13, max(8, len(important) * 0.32)))

    # Y 轴位置
    y_pos = list(range(len(important)))

    color_map = {
        'in_force': '#2E7D32',   # 绿:仍生效
        'expired': '#C62828',    # 红:已失效
        'future': '#1565C0',     # 蓝:未生效
    }

    # 绘条
    for i, item in enumerate(important):
        eff = item['eff']
        exp = item['exp'] or date(2030, 12, 31)  # 长期有效用 2030 占位
        no_expiry = item['exp'] is None
        color = color_map[item['status']]
        # 起始 / 长度
        x_start = (eff - date(2020, 1, 1)).days
        x_end = (exp - date(2020, 1, 1)).days
        width = x_end - x_start
        ax.barh(i, width, left=x_start, height=0.62, color=color, alpha=0.7,
                edgecolor='black', linewidth=0.4)
        # 长期有效:右侧加箭头
        if no_expiry:
            ax.annotate('', xy=(x_end + 60, i), xytext=(x_end, i),
                       arrowprops=dict(arrowstyle='->', color=color, lw=1.2))

    # X 轴:年份
    year_starts = []
    for y in range(2020, 2031):
        year_starts.append((date(y, 1, 1) - date(2020, 1, 1)).days)
    ax.set_xticks(year_starts)
    ax.set_xticklabels([str(y) for y in range(2020, 2031)], fontsize=9)

    # 报告日竖线
    today_x = (today - date(2020, 1, 1)).days
    ax.axvline(today_x, color='#FF6F00', linestyle='--', linewidth=2, alpha=0.85, zorder=3)
    ax.text(today_x + 25, len(important) - 0.3, f'报告日 {today.isoformat()}',
            color='#FF6F00', fontsize=10, fontweight='bold', va='top')

    # Y 轴标签
    labels = []
    for item in important:
        title = short_title(item['title'], 28)
        on = item['official']
        if on and len(on) < 25:
            label = f"⭐{item['imp']} {title}"
        else:
            label = f"⭐{item['imp']} {title}"
        labels.append(label)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()

    # 网格 + 标题
    ax.grid(axis='x', linestyle=':', alpha=0.4)
    ax.set_xlabel('年份', fontsize=11)
    ax.set_title(f'附录 A · 国家级重要政策生效周期 timeline(≥4 ⭐ + 本月 ≥4 省级,共 {len(important)} 条)',
                fontsize=13, fontweight='bold', pad=15)

    # 图例
    legend_elements = [
        mpatches.Patch(color='#2E7D32', alpha=0.7, label='仍生效'),
        mpatches.Patch(color='#C62828', alpha=0.7, label='已失效(政策真空期)'),
        mpatches.Patch(color='#1565C0', alpha=0.7, label='待生效'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10, framealpha=0.95)

    plt.tight_layout()
    out = CHARTS / "01_timeline.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  01_timeline.png ({len(important)} 条)")


# ============================================================
# 图 2:机会-风险 2x2 矩阵(11 march policies)
# ============================================================
def chart_2x2():
    fig, ax = plt.subplots(figsize=(11, 8))

    # 业务关键词
    biz_strong = ["V2G", "车网", "虚拟电厂", "充电", "充换电", "电力市场",
                  "电力交易", "辅助服务", "现货", "储能", "需求响应",
                  "加油", "成品油", "新能源汽车", "以旧换新", "设备更新"]

    points = []
    for d in march_detail:
        pid = d['id']
        fm = all_p.get(pid, {})
        imp = fm.get('重要性', 0) or 0
        title = fm.get('title', '')
        tags = fm.get('tags', []) or []
        full = title + ' ' + ' '.join(str(t) for t in tags)
        biz_hit = sum(1 for k in biz_strong if k in full)
        # X 轴:相关性(业务关键词命中数 + 重要性)
        relevance = min(5, biz_hit) + imp / 2
        # Y 轴:行动窗口(基于 effective_date 距报告日 / 重要性)
        e = eff_data.get(pid, {})
        eff = to_date(e.get('effective_date'))
        if eff:
            days_until = (eff - REPORT_DATE).days
            if days_until <= 0:  # 已生效
                window = 5  # 立即
            elif days_until <= 90:
                window = 3.5
            else:
                window = 2
        else:
            window = 1
        # 调整:imp 5 倾向"立即",imp 3 倾向"跟踪"
        window += (imp - 3) * 0.5

        # 名称 — 用政策全称简版,**不要 ID**
        short_name = short_title(title, 18)

        points.append({
            'name': short_name,
            'imp': imp,
            'relevance': relevance,
            'window': window,
            'level': (fm.get('region') or {}).get('level', '?'),
        })

    # 画散点
    for p in points:
        size = 200 + p['imp'] * 80
        color = {'国家': '#1976D2', '省': '#388E3C', '市': '#F57C00', '区': '#7B1FA2', '?': '#757575'}.get(p['level'], '#757575')
        ax.scatter(p['relevance'], p['window'], s=size, c=color,
                  alpha=0.65, edgecolors='black', linewidths=0.7)
        ax.annotate(p['name'], (p['relevance'], p['window']),
                    fontsize=8.5, ha='center', va='bottom',
                    xytext=(0, 9), textcoords='offset points')

    # 象限分割
    ax.axhline(3.5, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(4, color='gray', linestyle=':', alpha=0.5)

    # 象限标签
    ax.text(7.7, 5.5, '★ 趁早行动\n(强相关 + 趁早)', ha='center', fontsize=11,
            fontweight='bold', color='#C62828', alpha=0.85)
    ax.text(2.0, 5.5, '观察 / 跟踪\n(弱相关 + 趁早)', ha='center', fontsize=10,
            color='#757575', alpha=0.85)
    ax.text(7.7, 1.5, '研究 / 投资\n(强相关 + 中期)', ha='center', fontsize=10,
            color='#1565C0', alpha=0.85)
    ax.text(2.0, 1.5, '低优先 / 跟踪\n(弱相关 + 中期)', ha='center', fontsize=10,
            color='#757575', alpha=0.85)

    ax.set_xlabel('业务相关性 →', fontsize=12, fontweight='bold')
    ax.set_ylabel('行动窗口 趁早(高)/中期(低)', fontsize=12, fontweight='bold')
    ax.set_title('§7 · 3 月政策机会-风险 2×2 矩阵(11 篇)', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.grid(True, alpha=0.25)

    # 颜色图例(行政级别)
    legend_elements = [
        plt.scatter([], [], s=200, c='#1976D2', alpha=0.65, edgecolors='black', linewidths=0.7, label='国家级'),
        plt.scatter([], [], s=200, c='#388E3C', alpha=0.65, edgecolors='black', linewidths=0.7, label='省级'),
        plt.scatter([], [], s=200, c='#F57C00', alpha=0.65, edgecolors='black', linewidths=0.7, label='市级'),
        plt.scatter([], [], s=200, c='#7B1FA2', alpha=0.65, edgecolors='black', linewidths=0.7, label='区级'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10, framealpha=0.92)

    plt.tight_layout()
    out = CHARTS / "02_2x2_matrix.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  02_2x2_matrix.png")


# ============================================================
# 图 3:主题 × 31 省覆盖热力图
# ============================================================
def chart_heatmap():
    PROV = ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区",
            "辽宁省", "吉林省", "黑龙江省",
            "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
            "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
            "重庆市", "四川省", "贵州省", "云南省", "西藏自治区",
            "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区"]

    THEMES = [
        ("v2g", "V2G/车网"),
        ("power_market", "电力市场"),
        ("charging_infra", "充电基建"),
        ("new_ess", "新型储能"),
        ("equipment_renewal", "设备更新"),
    ]

    # entity 链接
    pol_entities = defaultdict(set)
    with open(VAULT / "1_extracted" / "entities" / "_extractions.jsonl", encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            pol_entities[d['policy_id']].add(d['canonical_id'])

    # 矩阵:行 = 主题,列 = 省份,值 = 政策数
    matrix = np.zeros((len(THEMES), len(PROV)))
    for pid, ents in pol_entities.items():
        fm = all_p.get(pid)
        if not fm: continue
        rname = (fm.get('region') or {}).get('name', '')
        if rname not in PROV: continue
        col = PROV.index(rname)
        for ti, (theme_id, _) in enumerate(THEMES):
            if theme_id in ents:
                matrix[ti][col] += 1

    fig, ax = plt.subplots(figsize=(15, 4))
    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')

    ax.set_xticks(range(len(PROV)))
    ax.set_xticklabels(PROV, rotation=55, ha='right', fontsize=8.5)
    ax.set_yticks(range(len(THEMES)))
    ax.set_yticklabels([t[1] for t in THEMES], fontsize=10)

    # 注释每格数字
    for i in range(len(THEMES)):
        for j in range(len(PROV)):
            if matrix[i][j] > 0:
                txt_color = 'white' if matrix[i][j] > matrix.max() * 0.5 else 'black'
                ax.text(j, i, f'{int(matrix[i][j])}', ha='center', va='center',
                        color=txt_color, fontsize=8, fontweight='bold')

    ax.set_title('附录 B · 重要政策主题 × 31 省覆盖热力图(单元格 = 该省该主题政策数)',
                fontsize=12, fontweight='bold', pad=12)
    plt.colorbar(im, ax=ax, label='政策数', shrink=0.7)

    plt.tight_layout()
    out = CHARTS / "03_regional_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  03_regional_heatmap.png")


# ============================================================
# 图 4:跨月演进脉络(国家 → 省级落地)
# ============================================================
def chart_evolution():
    fig, ax = plt.subplots(figsize=(13, 7))

    # 横轴:时间(2024.1 - 2026.4)
    # 纵轴:层级(国家 / 省级 / 市级)

    # 数据:从 march_detail 拿 national_source linkage
    # 简化版:几条主线
    lines = [
        # 主线 1:V2G
        {'name': 'NDRC 357《虚拟电厂指导意见》', 'level': '国家', 'date': '2025-04-11', 'imp': 5, 'group': 'V2G/VPP'},
        {'name': 'NDRC 718《车网互动试点》', 'level': '国家', 'date': '2024-09-10', 'imp': 5, 'group': 'V2G/VPP'},
        {'name': '上海松江能源行动方案 ★', 'level': '省', 'date': '2026-03-13', 'imp': 3, 'group': 'V2G/VPP'},
        {'name': '山东 VPP 高质量发展方案 ★', 'level': '省', 'date': '2026-03-27', 'imp': 4, 'group': 'V2G/VPP'},
        # 主线 2:充电基建
        {'name': 'NDRC 1015《三年倍增》', 'level': '国家', 'date': '2025-10-15', 'imp': 5, 'group': '充电基建'},
        {'name': '宁夏充电基建实施方案 ★', 'level': '省', 'date': '2026-03-20', 'imp': 4, 'group': '充电基建'},
        # 主线 3:电力市场
        {'name': 'NDRC 1656《电力中长期市场基本规则》', 'level': '国家', 'date': '2025-12-17', 'imp': 5, 'group': '电力市场'},
        {'name': '十五五规划纲要 ★', 'level': '国家', 'date': '2026-03-13', 'imp': 5, 'group': '电力市场'},
        {'name': '2026 政府工作报告 ★', 'level': '国家', 'date': '2026-03-05', 'imp': 5, 'group': '电力市场'},
        # 主线 4:乡村
        {'name': '能源局乡村振兴会议 ★', 'level': '国家', 'date': '2026-03-04', 'imp': 3, 'group': '乡村'},
    ]

    level_y = {'国家': 3, '省': 2, '市': 1, '区': 0.5}
    group_color = {'V2G/VPP': '#1976D2', '充电基建': '#388E3C', '电力市场': '#C62828', '乡村': '#7B1FA2'}

    # 转日期
    def d2x(s):
        d = date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        return (d - date(2024, 1, 1)).days

    # 画连线(同 group)
    by_group = defaultdict(list)
    for ln in lines:
        by_group[ln['group']].append(ln)

    for g, items in by_group.items():
        items_sorted = sorted(items, key=lambda x: x['date'])
        for i in range(len(items_sorted) - 1):
            a = items_sorted[i]
            b = items_sorted[i + 1]
            ax.plot([d2x(a['date']), d2x(b['date'])],
                    [level_y[a['level']], level_y[b['level']]],
                    color=group_color[g], alpha=0.4, linestyle='-', linewidth=1.5, zorder=1)

    # 画点
    for ln in lines:
        x = d2x(ln['date'])
        y = level_y[ln['level']]
        size = 250 + ln['imp'] * 100
        is_march = ln['name'].endswith('★')
        ax.scatter(x, y, s=size, c=group_color[ln['group']], alpha=0.85,
                   edgecolors='red' if is_march else 'black',
                   linewidths=2.5 if is_march else 0.7, zorder=3)
        # 标签
        ax.annotate(ln['name'].rstrip(' ★'), (x, y),
                    fontsize=8, ha='center', va='bottom',
                    xytext=(0, 14), textcoords='offset points')

    # 报告月标记
    march_start = d2x('2026-03-01')
    march_end = d2x('2026-03-31')
    ax.axvspan(march_start, march_end, alpha=0.13, color='orange', zorder=0)
    ax.text((march_start + march_end) / 2, 0.05, '2026-03',
            ha='center', fontsize=10, fontweight='bold', color='#E65100')

    # 轴
    ax.set_yticks([0.5, 1, 2, 3])
    ax.set_yticklabels(['区', '市', '省', '国家'], fontsize=11)
    ax.set_ylim(0, 4)

    # X 轴:每季度
    quarters = []
    qlabels = []
    for y in [2024, 2025, 2026]:
        for m in [1, 4, 7, 10]:
            d = date(y, m, 1)
            x = (d - date(2024, 1, 1)).days
            quarters.append(x)
            qlabels.append(f'{y}-{m:02d}')
    ax.set_xticks(quarters)
    ax.set_xticklabels(qlabels, rotation=35, ha='right', fontsize=9)

    ax.set_title('§5 · 跨月演进脉络:国家级 → 省级落地(★ = 3 月新政,红框)',
                fontsize=13, fontweight='bold', pad=15)
    ax.grid(axis='y', linestyle=':', alpha=0.4)

    legend = [mpatches.Patch(color=c, alpha=0.85, label=g) for g, c in group_color.items()]
    ax.legend(handles=legend, loc='upper left', fontsize=10, framealpha=0.92)

    plt.tight_layout()
    out = CHARTS / "04_evolution_chain.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  04_evolution_chain.png")


# ============================================================
# 图 5:近 6 月政策密度对比
# ============================================================
def chart_monthly_compare():
    months = ['2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03']
    counts = []
    high_imp = []
    for m in months:
        c = sum(1 for fm in all_p.values() if str(fm.get('date', '')).startswith(m))
        h = sum(1 for fm in all_p.values()
                if str(fm.get('date', '')).startswith(m) and (fm.get('重要性', 0) or 0) >= 4)
        counts.append(c)
        high_imp.append(h)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(months))
    width = 0.35

    b1 = ax.bar(x - width/2, counts, width, label='全部政策', color='#90CAF9', edgecolor='#1565C0')
    b2 = ax.bar(x + width/2, high_imp, width, label='重要政策(⭐≥4)', color='#FFAB91', edgecolor='#C62828')

    for i, (c1, c2) in enumerate(zip(counts, high_imp)):
        ax.text(i - width/2, c1 + 0.4, str(c1), ha='center', fontsize=10, fontweight='bold')
        ax.text(i + width/2, c2 + 0.4, str(c2), ha='center', fontsize=10, fontweight='bold')

    # 高亮 3 月
    ax.axvspan(len(months) - 1.5, len(months) - 0.5, alpha=0.15, color='orange')
    ax.text(len(months) - 1, max(counts) - 1, '本月', ha='center',
            fontsize=11, fontweight='bold', color='#E65100')

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=10)
    ax.set_ylabel('政策数', fontsize=11)
    ax.set_title('§1 · 近 6 月政策密度对比', fontsize=13, fontweight='bold', pad=12)
    ax.legend(fontsize=10, framealpha=0.92)
    ax.grid(axis='y', linestyle=':', alpha=0.4)

    plt.tight_layout()
    out = CHARTS / "05_monthly_compare.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  05_monthly_compare.png")


# ============================================================
# 图 6:本月政策业务相关性饼图
# ============================================================
def chart_relevance_pie():
    biz_strong = ["V2G", "车网", "虚拟电厂", "充电", "充换电", "电力市场",
                  "电力交易", "辅助服务", "现货", "储能", "需求响应",
                  "加油", "成品油", "新能源汽车", "以旧换新", "设备更新"]

    strong = 0; medium = 0; weak = 0
    for d in march_detail:
        pid = d['id']
        fm = all_p.get(pid, {})
        imp = fm.get('重要性', 0) or 0
        title = fm.get('title', '')
        tags = fm.get('tags', []) or []
        full = title + ' ' + ' '.join(str(t) for t in tags)
        hits = sum(1 for k in biz_strong if k in full)
        if imp >= 4 and hits >= 1:
            strong += 1
        elif imp == 3 and hits >= 1:
            medium += 1
        else:
            weak += 1

    sizes = [strong, medium, weak]
    labels = [f'强相关\n⭐≥4 + 业务命中\n{strong} 篇',
              f'中相关\n⭐3 + 业务命中\n{medium} 篇',
              f'弱相关\n{weak} 篇']
    colors = ['#C62828', '#F57C00', '#90A4AE']
    explode = (0.06, 0.03, 0)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, colors=colors, explode=explode,
           autopct='%1.0f%%', startangle=90, textprops={'fontsize': 11},
           wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    ax.set_title(f'§3 · 3 月政策业务相关性分布(总 {sum(sizes)} 篇)',
                 fontsize=13, fontweight='bold', pad=15)

    plt.tight_layout()
    out = CHARTS / "06_relevance_pie.png"
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  06_relevance_pie.png")


# 运行
if __name__ == "__main__":
    print("Rendering 6 charts...")
    chart_timeline()
    chart_2x2()
    chart_heatmap()
    chart_evolution()
    chart_monthly_compare()
    chart_relevance_pie()
    print(f"\n✅ All charts saved to {CHARTS}")
