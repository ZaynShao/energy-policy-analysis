#!/usr/bin/env python3
"""
render_html.py
HTML 版月报 — 与 docx 同源(_docx_data.json + charts/*.png)。
单文件输出,charts 内联 base64,便于邮件 / 共享盘转发。
输出:~/Desktop/能源政策月报-2026-03.html
"""

import json
import base64
from pathlib import Path
from html import escape

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
DATA_PATH = VAULT / "_meta" / "march_report_batches" / "_docx_data.json"
CHARTS_DIR = VAULT / "_meta" / "march_report_batches" / "charts"
OUT_PATH = Path.home() / "Desktop" / "能源政策月报-2026-03.html"

data = json.load(open(DATA_PATH, encoding='utf-8'))

COLOR = {
    'primary': '#1565C0',
    'accent': '#C62828',
    'warning': '#F57C00',
    'success': '#2E7D32',
    'gray': '#616161',
}


def chart_b64(filename):
    p = CHARTS_DIR / filename
    if not p.exists():
        return ''
    return 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode()


def chart_img(filename, max_w='600px'):
    src = chart_b64(filename)
    if not src:
        return f'<p style="color:#C62828">[图缺失:{filename}]</p>'
    return f'<img src="{src}" alt="{filename}" style="max-width:{max_w};width:100%;display:block;margin:1.5em auto;">'


def traffic_label(imp):
    if imp >= 5: return '[趁早行动]', COLOR['accent'], 'red'
    if imp >= 4: return '[研究 / 跟进]', COLOR['warning'], 'yellow'
    if imp == 3: return '[跟踪]', COLOR['success'], 'green'
    return '[关注]', COLOR['gray'], 'gray'


def short_prov(name):
    """北京市 / 内蒙古自治区 / 宁夏回族自治区 → 北京 / 内蒙古 / 宁夏"""
    return (name.replace('省', '').replace('市', '').replace('自治区', '')
                .replace('壮族', '').replace('回族', '').replace('维吾尔', ''))


CSS = """
* { box-sizing: border-box; }
body {
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif;
  max-width: 920px;
  margin: 0 auto;
  padding: 2em 2em 5em;
  color: #222;
  line-height: 1.7;
  font-size: 15px;
  background: #FAFAFA;
}
.cover {
  text-align: center;
  padding: 4em 1em 3em;
  background: white;
  border-radius: 8px;
  margin-bottom: 2em;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.cover-title { font-size: 3em; color: #1565C0; margin: 0 0 0.3em; font-weight: 700; }
.cover-subtitle { font-size: 1.8em; color: #444; margin: 0 0 2em; font-weight: 400; }
.cover-meta { color: #616161; font-size: 0.95em; margin: 0.3em 0; }

main { background: white; padding: 2em 2.5em; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }

h1 {
  color: #1565C0;
  border-bottom: 2px solid #1565C0;
  padding-bottom: 0.3em;
  margin-top: 2em;
  margin-bottom: 1em;
  font-size: 1.55em;
}
h1:first-of-type { margin-top: 0; }
h2 {
  color: #1565C0;
  font-size: 1.2em;
  margin-top: 1.8em;
  margin-bottom: 0.6em;
}
h3 {
  color: #444;
  font-size: 1.05em;
  margin-top: 1.3em;
  margin-bottom: 0.5em;
}
p { margin: 0.6em 0; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 0.92em;
}
th {
  background: #E3F2FD;
  border: 1px solid #BCD;
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  color: #1565C0;
}
td {
  border: 1px solid #DDD;
  padding: 7px 10px;
  vertical-align: top;
}
tr:nth-child(even) td { background: #FAFBFC; }

ul { margin: 0.5em 0 1em; padding-left: 1.5em; }
li { margin: 0.3em 0; }

.card {
  border: 1px solid #DDD;
  border-left: 4px solid #1565C0;
  padding: 1em 1.3em;
  margin: 1.2em 0;
  border-radius: 4px;
  background: #FAFBFC;
}
.card.red    { border-left-color: #C62828; background: #FFF5F5; }
.card.yellow { border-left-color: #F57C00; background: #FFFBF0; }
.card.green  { border-left-color: #2E7D32; background: #F4FBF4; }
.card .head {
  font-weight: 700;
  font-size: 1.05em;
  margin-bottom: 0.5em;
}
.card .meta { color: #616161; font-size: 0.88em; margin-bottom: 0.6em; }

.muted { color: #888; font-size: 0.88em; }
.italic { font-style: italic; }
.note { color: #666; font-size: 0.92em; font-style: italic; margin: 0.6em 0; }
.gray { color: #757575; }
.warn { color: #C62828; font-weight: 600; }

.toc {
  background: #F5F8FB;
  padding: 1em 1.5em;
  border-radius: 6px;
  margin-bottom: 2em;
  border: 1px solid #DCE7F1;
}
.toc h2 { margin-top: 0; color: #1565C0; }
.toc ul { list-style: none; padding-left: 0.5em; }
.toc li { padding: 0.15em 0; }
.toc a { color: #1565C0; text-decoration: none; }
.toc a:hover { text-decoration: underline; }

@media (max-width: 720px) {
  body { padding: 1em; }
  main { padding: 1em; }
  .cover-title { font-size: 2em; }
}
@media print {
  body { padding: 0; max-width: none; background: white; }
  main, .cover { box-shadow: none; padding: 0; }
  h1 { page-break-before: always; }
  h1:first-of-type { page-break-before: avoid; }
}
"""


# ============================================================
# Build HTML
# ============================================================
out = []
out.append(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>能源政策月报 2026-03</title>
<style>{CSS}</style>
</head>
<body>""")

meta = data['meta']
out.append(f"""
<div class="cover">
  <div class="cover-title">能源政策月报</div>
  <div class="cover-subtitle">2026 年 3 月</div>
  <div class="cover-meta">报告日期:{data['report_date']}</div>
  <div class="cover-meta">本月入库政策 {meta['march_count']} 篇 · 强相关 {meta['march_strong']} · 中相关 {meta['march_medium']} · 弱/无相关 {meta['march_weak']}</div>
</div>
<main>
""")

# === TOC ===
out.append("""
<div class="toc">
<h2>目录</h2>
<ul>
  <li><a href="#s1">§ 1 月度速览</a></li>
  <li><a href="#s2">§ 2 决策卡片</a></li>
  <li><a href="#s3">§ 3 政策全列表</a></li>
  <li><a href="#s4">§ 4 重点解读 — 国家级新政</a></li>
  <li><a href="#s5">§ 5 省级落地证据(国家级追溯)</a></li>
  <li><a href="#s6">§ 6 机会-风险 2×2 矩阵</a></li>
  <li><a href="#s7">§ 7 缺口 / 盲区警示</a></li>
  <li><a href="#s8">§ 8 下月 watching list</a></li>
  <li><a href="#sa">附录 A · 国家级重要政策生效周期</a></li>
  <li><a href="#sb">附录 B · 重要政策各省覆盖度</a></li>
</ul>
</div>
""")

# === §1 月度速览 ===
out.append('<h1 id="s1">§ 1 月度速览</h1>')
out.append('<h2>1.1 数字一览</h2>')
out.append('<table><thead><tr><th>月份</th><th>入库政策数</th><th>重要政策(⭐≥4)</th></tr></thead><tbody>')
for m in data['monthly_compare']:
    out.append(f"<tr><td>{m['month']}</td><td>{m['count']}</td><td>{m['high_imp']}</td></tr>")
out.append('</tbody></table>')
out.append(chart_img('05_monthly_compare.png', max_w='600px'))

out.append('<h2>1.2 本月最重要 2 件事</h2>')
highlights = [
    ('一 · 国家级最高规格政策密集落地',
     '本月《2026 年政府工作报告》(3-5)+《十五五规划纲要》(3-13)同期出台,与政府工作报告中"新型储能装机超 1.3 亿千瓦、非化石能源占比 21.7%、单位 GDP 碳强度累计降 17%"的量化承诺联动,为公司三大业务(加油 / 充电 / 电力,后者含储能·V2G·电力交易)提供 5 年顶层政策授权。'),
    ('二 · 国家级动向的省级落地',
     '山东省虚拟电厂高质量发展方案(3-27)是 NDRC 357 号《虚拟电厂指导意见》之后省级第 2 个 VPP 专项(前序:上海《用户侧虚拟电厂建设实施方案 2025-2027 年》沪经信运〔2025〕407 号 2025-06-19),2027 年 200 万 kW / 2030 年 400 万 kW 量化目标具体;宁夏年度充电方案(3-20)是 NDRC 1015《三年倍增》在西北 5 省空白首破。两条省级动向均属"国家级文件落地节奏"的关键时点信号。'),
]
for h, body in highlights:
    out.append(f'<div class="card"><div class="head" style="color:#1565C0">{h}</div><p>{body}</p></div>')

# === §2 决策卡片 ===
out.append('<h1 id="s2">§ 2 决策卡片</h1>')
out.append('<p class="note">本月 11 篇政策中,重要性 ⭐≥4 且业务直接相关的 4 篇 — 决策层第一时间需要做判断。其他 5 篇中相关 + 2 篇弱相关详见 §3 全列表。</p>')

strong = [m for m in data['march_list'] if m['category'] == 'strong']
for i, p in enumerate(strong, 1):
    label, color, css_class = traffic_label(p['importance'])
    out.append(f'<div class="card {css_class}">')
    out.append(f'<div class="head" style="color:{color}">卡片 {i} · {label}</div>')
    out.append(f'<div style="font-weight:600;font-size:1.02em">政策:{escape(p["title"])}</div>')
    out.append(f'<div class="meta">日期:{p["date"]} · 发文:{escape(" / ".join(p["issuer"]))} · 区域:{p["region"]} · 重要性:{p["importance"]}/5{(" · " + escape(p["official"])) if p.get("official") else ""}</div>')
    out.append(f'<p>政策核心:{escape(p["core_one_line"])}</p>')
    out.append(f'<p>公司影响:{escape(p["didi_impact_one_line"])}</p>')
    if p.get('action_recommendations'):
        out.append('<p style="font-weight:600;margin-bottom:0.2em">行动建议:</p><ul>')
        for act in p['action_recommendations'][:3]:
            out.append(f'<li>{escape(act)}</li>')
        out.append('</ul>')
    ns_title = (p.get('national_source') or {}).get('national_source_id_or_title')
    if ns_title:
        out.append(f'<p class="muted italic">国家级源头:{escape(ns_title)}</p>')
    out.append('</div>')

# === §3 政策全列表 ===
out.append('<h1 id="s3">§ 3 政策全列表</h1>')
out.append(chart_img('06_relevance_pie.png', max_w='480px'))

for sub_id, sub_title, cat in [('3.1', '强相关 ⭐≥4 + 业务命中', 'strong'),
                                ('3.2', '中相关 ⭐3 + 业务命中', 'medium'),
                                ('3.3', '弱相关 / 业务无关', 'weak')]:
    out.append(f'<h2>{sub_id} {sub_title}</h2>')
    rows = [m for m in data['march_list'] if m['category'] == cat]
    out.append('<table><thead><tr><th>发布日</th><th>区域</th><th>⭐</th><th>标题</th><th>业务命中</th></tr></thead><tbody>')
    for m in rows:
        if cat == 'weak':
            biz = '弱命中' if m['biz_kws'] else '无命中'
        else:
            biz = '/'.join(m['biz_kws'][:4])
        out.append(f"<tr><td>{m['date']}</td><td>{m['region']}</td><td>⭐{m['importance']}</td><td>{escape(m['title'][:35])}</td><td>{escape(biz)}</td></tr>")
    out.append('</tbody></table>')

# === §4 重点解读 ===
out.append('<h1 id="s4">§ 4 重点解读 — 国家级新政</h1>')
out.append('<p class="note">本月 3 篇国家级最高规格新政详读:政策核心、对公司三大业务影响、行动建议。</p>')
march_by_id = {m['id']: m for m in data['march_list']}
labels = {
    '加油': '加油业务',
    '充电': '充电业务',
    '电力_储能_V2G_交易': '电力业务(储能 / V2G / 电力交易)',
}
for idx, pid in enumerate(data['deep_dive_ids'], 1):
    p = march_by_id.get(pid)
    if not p: continue
    out.append(f'<h2>4.{idx} 《{escape(p["title"])}》</h2>')
    out.append(f'<div class="meta">日期:{p["date"]} · 发文:{escape(" / ".join(p["issuer"]))} · 重要性:{p["importance"]}/5{(" · " + escape(p["official"])) if p.get("official") else ""}</div>')
    out.append('<h3 style="color:#1565C0">一 · 政策核心</h3>')
    out.append(f'<p>{escape(p.get("summary_2_3") or p.get("core_one_line", ""))}</p>')
    out.append('<h3 style="color:#1565C0">二 · 对公司三大业务影响</h3>')
    bi = p.get('biz_impact', {}) or {}
    out.append('<ul>')
    for k in ['加油', '充电', '电力_储能_V2G_交易']:
        v = bi.get(k)
        if v and v != '无直接影响':
            out.append(f'<li><strong>{labels[k]}:</strong>{escape(v)}</li>')
    rural = bi.get('乡村')
    if rural and rural != '无直接影响':
        out.append(f'<li class="gray"><strong>乡村能源(关注方向,非业务线):</strong>{escape(rural)}</li>')
    out.append('</ul>')
    if p.get('action_recommendations'):
        out.append('<h3 style="color:#1565C0">三 · 行动建议</h3><ul>')
        for act in p['action_recommendations']:
            out.append(f'<li>{escape(act)}</li>')
        out.append('</ul>')
    ns = p.get('national_source') or {}
    if ns.get('is_national_level_originated'):
        out.append('<h3 style="color:#1565C0">四 · 政策定位</h3>')
        out.append(f'<p class="muted italic">本政策为国家级最高规格文件本身。{escape(ns.get("linkage", ""))}</p>')

# === §5 省级落地证据 ===
out.append('<h1 id="s5">§ 5 省级落地证据(国家级追溯)</h1>')
out.append('<p>本月省/市级政策追溯到的国家级源头政策——多数源自 2023-2025 年早期国家级路径,而非本月新政。本月 3 篇国家级新政(政府工作报告 / 十五五 / 乡村振兴会议)与省级政策属"同源并行",非"派生因果":省级专项起草周期 6-12 月,物理上不可能响应同月国家级。下表呈现追溯链条与 linkage 类型(直接落地 / 补充细化 / 同向部署)。</p>')
out.append(chart_img('04_evolution_chain.png', max_w='540px'))

out.append('<h2>5.1 ⭐≥4 省级政策 → 国家级源头</h2>')
out.append('<table><thead><tr><th>省级政策</th><th>文号·日期</th><th>业务线</th><th>国家级源头</th><th>linkage 类型</th></tr></thead><tbody>')
for e in data['evolution_chains']:
    pol_col = f"{e['march_region']} {e['march_title'][:18]}"
    od_col = f"{e['march_official']} · {e['march_date']}" if e.get('march_official') else e['march_date']
    out.append(f"<tr><td>{escape(pol_col)}</td><td>{escape(od_col)}</td><td>{e.get('biz_line','综合')}</td><td>{escape(e['national_source'][:35])}</td><td>{e.get('linkage_type','同向部署')}</td></tr>")
out.append('</tbody></table>')
out.append('<p class="note">linkage 类型说明:直接落地 = 省级文本直接引用国家级文号;补充细化 = 主题对齐且条款扩展(地方实施细则常见);同向部署 = 主题、目标、节奏与国家级路径吻合,无显式引用。</p>')

# === §6 2×2 ===
out.append('<h1 id="s6">§ 6 机会-风险 2×2 矩阵</h1>')
out.append('<p>11 篇 3 月政策按"业务相关性 × 行动窗口"两维分布。</p>')
out.append(chart_img('02_2x2_matrix.png', max_w='540px'))

# === §7 缺口/盲区 ===
out.append('<h1 id="s7">§ 7 缺口 / 盲区警示</h1>')
out.append(chart_img('03_regional_heatmap.png', max_w='800px'))

out.append('<h2>7.1 主题 × 31 省覆盖概览</h2>')
out.append('<table><thead><tr><th>主题</th><th>覆盖省份数</th><th>覆盖率</th><th>空白(前 5)</th></tr></thead><tbody>')
for theme, c in data['theme_coverage'].items():
    blank5 = '/'.join(short_prov(p) for p in c['blank_provs'][:5])
    cov = f"{c['covered_count']}/31"
    pct = f"{round(c['covered_count']/31*100)}%"
    out.append(f"<tr><td>{theme}</td><td>{cov}</td><td>{pct}</td><td>{blank5}</td></tr>")
out.append('</tbody></table>')

out.append('<h2>7.2 本月新填空白</h2>')
out.append('<ul>')
out.append('<li><strong>充电基建:</strong>宁夏首破(西北 5/5 空白省份之一)— 但毗邻甘青陕蒙仍空白</li>')
out.append('<li><strong>电力市场 / 虚拟电厂:</strong>山东加深覆盖(NDRC 357 后省级第 2 个 VPP 专项,前序:上海 沪经信运〔2025〕407 号 2025-06)</li>')
out.append('</ul>')

out.append('<h2>7.3 持续盲区(高严重度)</h2><ul>')
for g in [g for g in data['gaps'] if g['severity'] == 'high'][:5]:
    blank = ' / '.join(short_prov(p) for p in g['blank'])
    out.append(f'<li class="warn">[{g["theme"]}] {g["region"]}:{blank}</li>')
out.append('</ul>')

# === §8 watching list ===
out.append('<h1 id="s8">§ 8 下月 watching list</h1>')
out.append('<p class="note">基于政策窗口期 + 历史关系网推断 4 月可能出台或落地的政策。</p>')
out.append('<table><thead><tr><th>优先级</th><th>关注事项</th><th>预期窗口</th><th>理由</th></tr></thead><tbody>')
for w in data['watching']:
    out.append(f"<tr><td>{w['priority']}</td><td>{escape(w['item'])}</td><td>{w['expected_window']}</td><td>{escape(w['rationale'])}</td></tr>")
out.append('</tbody></table>')

# === 附录 A ===
out.append('<h1 id="sa">附录 A · 国家级重要政策生效周期</h1>')
out.append(f'<p>报告日 2026-03-31 视角:国家级 ⭐≥4 政策中,<strong>{meta["total_in_force_ge4_national"]}</strong> 篇仍生效,<strong>{meta["total_expired_ge4_national"]}</strong> 篇已失效(可能进入"政策真空期")。</p>')
out.append(chart_img('01_timeline.png', max_w='800px'))

out.append('<h2>A1 已失效政策(政策真空期警示)</h2>')
out.append('<table><thead><tr><th>政策标题</th><th>生效日</th><th>失效日</th><th>已过期</th></tr></thead><tbody>')
for e in data['expired_national'][:12]:
    out.append(f"<tr><td>{escape(e['title'][:30])}</td><td>{e.get('effective_date','?')}</td><td>{e.get('expires_at','?')}</td><td>{e.get('days_expired',0)} 天</td></tr>")
out.append('</tbody></table>')

# === 附录 B ===
out.append('<h1 id="sb">附录 B · 重要政策各省覆盖度</h1>')
out.append('<p>5 大主题 × 31 省级行政区覆盖矩阵(单元格 = 该主题在该省的政策数量)。</p>')
out.append(chart_img('03_regional_heatmap.png', max_w='800px'))

out.append('<h2>B.1 各主题覆盖详情</h2>')
for theme, c in data['theme_coverage'].items():
    out.append(f'<h3 style="color:#1565C0">{theme}</h3>')
    out.append(f"<p><strong>已覆盖({c['covered_count']}):</strong>{' / '.join(short_prov(p) for p in c['covered_provs'])}</p>")
    out.append(f"<p class=\"muted\"><strong>空白({c['blank_count']}):</strong>{' / '.join(short_prov(p) for p in c['blank_provs'])}</p>")

out.append('<h2>B.2 本月新政在 31 省的扩散预期</h2><ul>')
out.append('<li>山东 VPP → 预计跟随省份:广东 / 江苏 / 浙江(经济发达 + 电力交易市场成熟)</li>')
out.append('<li>宁夏充电 → 预计跟随省份:陕西 / 甘肃 / 青海(西北邻省,产业空白接续)</li>')
out.append('</ul>')

out.append('</main></body></html>')

OUT_PATH.write_text('\n'.join(out), encoding='utf-8')
size_kb = OUT_PATH.stat().st_size / 1024
print(f"HTML 月报已生成:")
print(f"   {OUT_PATH}")
print(f"   {size_kb:.1f} KB")
