#!/usr/bin/env python3
"""
prep_docx_data.py
为 docx 渲染准备所有数据,输出统一 JSON。
"""

import json
import re
import yaml
from pathlib import Path
from datetime import date
from collections import Counter, defaultdict

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
BATCHES = VAULT / "_meta" / "march_report_batches"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

REPORT_DATE = "2026-03-31"


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        return yaml.safe_load(m.group(1)) or {}, text[m.end():]
    except yaml.YAMLError:
        return None, text


def short(s, n):
    if not s: return ""
    s = re.sub(r'\s+', ' ', s.strip())
    return s if len(s) <= n else s[:n] + "..."


def sanitize_biz_framing(text):
    """统一对内表述:
    - 三大业务 = 加油 / 充电 / 电力(后者含储能·V2G·电力交易);乡村是关注方向(非业务线)
    - "滴滴/滴滴能源" → "公司"(对内描述,不用品牌名)
    - "立即行动 / A 立即" → "趁早行动 / A 趁早"(行动分类用语,弱化紧迫性的过激感)
    """
    if not text: return text
    # 业务框架修正
    text = text.replace('四大业务线', '三大业务')
    text = text.replace('四大业务', '三大业务')
    text = re.sub(r'([四五六七八九])(条|大)业务线', r'\1个业务方向', text)
    # 品牌→对内"公司"
    text = text.replace('滴滴能源', '公司')
    text = text.replace('滴滴', '公司')
    # 立即→趁早
    text = text.replace('立即行动', '趁早行动')
    text = text.replace('A 立即', 'A 趁早')
    text = text.replace('A立即', 'A趁早')
    return text


# 加载所有政策
all_p = {}
for f in (VAULT / "0_raw" / "policies").glob("*.md"):
    text = f.read_text(encoding='utf-8')
    fm, body = parse_fm(text)
    if fm and fm.get('id'):
        all_p[fm['id']] = {'fm': fm, 'body': body, 'filename': f.name}

# 加载 consolidated
with open(BATCHES / "_consolidated.json", encoding='utf-8') as f:
    cdata = json.load(f)
eff_data = cdata['effective_data']
march_detail = cdata['march_detail']

# Build march detail by id
march_by_id = {d['id']: d for d in march_detail}

# 业务关键词
BIZ_STRONG = ["V2G", "车网", "虚拟电厂", "充电", "充换电", "电力市场", "电力交易",
              "辅助服务", "现货", "储能", "需求响应", "加油", "成品油",
              "新能源汽车", "以旧换新", "设备更新"]


# ============================================================
# 1. § 1 月度速览数据
# ============================================================
month_count = Counter()
month_high = Counter()
for pid, d in all_p.items():
    dt = str(d['fm'].get('date') or '')
    if len(dt) >= 7:
        month_count[dt[:7]] += 1
        if (d['fm'].get('重要性', 0) or 0) >= 4:
            month_high[dt[:7]] += 1


# ============================================================
# 2. § 3 政策全列表(11 政策按强/中/弱)
# ============================================================
march_pids = [pid for pid in all_p if str(all_p[pid]['fm'].get('date', '')).startswith('2026-03')]

def relevance(fm):
    title = fm.get('title', '')
    tags = ' '.join(str(t) for t in (fm.get('tags') or []))
    return [k for k in BIZ_STRONG if k in (title + ' ' + tags)]

march_list = []
for pid in march_pids:
    fm = all_p[pid]['fm']
    imp = fm.get('重要性', 0) or 0
    kws = relevance(fm)
    detail = march_by_id.get(pid, {})
    if imp >= 4 and kws:
        cat = 'strong'
    elif imp == 3 and kws:
        cat = 'medium'
    else:
        cat = 'weak'
    march_list.append({
        'id': pid,
        'title': fm.get('title', ''),
        'date': str(fm.get('date', '')),
        'official': fm.get('official_number', '') or '',
        'issuer': fm.get('issuer', []) or [],
        'region': fm.get('region', {}).get('name', '?') or '?',
        'region_level': fm.get('region', {}).get('level', '?') or '?',
        'importance': imp,
        'tags': fm.get('tags', []) or [],
        'biz_kws': kws,
        'category': cat,
        'core_one_line': sanitize_biz_framing(detail.get('core_in_one_line', '')),
        'didi_impact_one_line': sanitize_biz_framing(detail.get('didi_impact_in_one_line', '')),
        'summary_2_3': sanitize_biz_framing(detail.get('summary_2_3_lines', '')),
        'biz_impact': {k: sanitize_biz_framing(v) for k, v in (detail.get('biz_impact', {}) or {}).items()},
        'action_recommendations': [sanitize_biz_framing(a) for a in detail.get('action_recommendations', [])],
        'national_source': detail.get('national_source', {}),
        'reading_value': detail.get('reading_value', ''),
    })

march_list.sort(key=lambda p: (-p['importance'], p['date']))


# ============================================================
# 3. § 4 重点解读 Top 3 — 国家级新政 + 省级落地证据(方案 C 核心)
# ============================================================
# 用户拍板:重点解读 = 3 篇国家级新政(政府工作报告 / 十五五规划纲要 / 乡村振兴会议)
# 省级政策当作"国家级落地证据"展示
DEEP_DIVE_IDS = []
for pid in ['P_2026_SC_0305e288', 'P_2026_NPC_03132f88', 'P_2026_NEA_0304ed54']:
    if pid in march_by_id:
        DEEP_DIVE_IDS.append(pid)

# 给每篇国家级新政追加"省级落地证据"清单
DEEP_DIVE_KEYWORDS = {
    'P_2026_SC_0305e288': ['政府工作报告', '李强', '工作报告'],  # 政府工作报告
    'P_2026_NPC_03132f88': ['十五五', '规划纲要', '十五个五年', '美丽中国', '碳达峰'],  # 十五五规划
    'P_2026_NEA_0304ed54': ['乡村振兴', '中央一号文件', '农村', '县域'],  # 乡村振兴会议
}

deep_dive_witnesses = {}
for deep_pid in DEEP_DIVE_IDS:
    keywords = DEEP_DIVE_KEYWORDS.get(deep_pid, [])
    witnesses = []
    # 扫所有 march_list 里的非国家级政策(都是 evolution_chains 的来源)
    for chain in []:  # placeholder, fill below
        pass
    # 直接从 march_list 找:其 national_source.national_source_id_or_title 或 linkage_full 里包含本国家级政策的关键词
    for m in march_list:
        ns = m.get('national_source', {})
        if not ns: continue
        # 严格:仅省/市/区级算"省级落地证据"(国家级 / 未知 不算)
        if m['region_level'] not in ['省', '市', '区']: continue
        full_text = (ns.get('national_source_id_or_title', '') + ' ' +
                     str(ns.get('linkage', '')) + ' ' +
                     str(ns.get('evidence', '')))
        if any(kw in full_text for kw in keywords):
            witnesses.append({
                'march_id': m['id'],
                'march_title': m['title'],
                'march_region': m['region'],
                'march_region_level': m['region_level'],
                'march_importance': m['importance'],
                'linkage_type': '直接落地' if '直接落地' in ns.get('linkage', '') else (
                                '借鉴框架' if '借鉴框架' in ns.get('linkage', '') else (
                                '主题对应' if '主题对应' in ns.get('linkage', '') else '关联')),
                'evidence': ns.get('evidence', '')[:120],
            })
    deep_dive_witnesses[deep_pid] = witnesses

# 政府工作报告特殊处理:发布于 3-5,本月省级可能未直接引用 — 列所有省级 march 政策做"主题对应"补全
if 'P_2026_SC_0305e288' in deep_dive_witnesses and len(deep_dive_witnesses['P_2026_SC_0305e288']) == 0:
    fallback = []
    for m in march_list:
        if m['region_level'] not in ['省', '市', '区']: continue
        fallback.append({
            'march_id': m['id'],
            'march_title': m['title'],
            'march_region': m['region'],
            'march_region_level': m['region_level'],
            'march_importance': m['importance'],
            'linkage_type': '主题对应*',  # * = fallback,非 Agent 抽出的直接引用
            'evidence': '政府工作报告 3-5 发布,本月省级政策尚未直接引用,但与其顶层定调主题对应',
        })
    deep_dive_witnesses['P_2026_SC_0305e288'] = fallback

# 乡村振兴会议:也可补充扩展 — 实际 0 直接证据是合理(乡村会议 3-4 发布,后续地方动作未到位)
if 'P_2026_NEA_0304ed54' in deep_dive_witnesses:
    # 滤掉国家级(小水电)
    cleaned = [w for w in deep_dive_witnesses['P_2026_NEA_0304ed54']
               if w['march_region_level'] in ['省', '市', '区']]
    deep_dive_witnesses['P_2026_NEA_0304ed54'] = cleaned


# ============================================================
# 4. 附录 A timeline 数据(简化:仅给国家级 ≥4 仍生效)
# ============================================================
def to_date_obj(s):
    if not s: return None
    try: return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except: return None

REPORT_DT = to_date_obj(REPORT_DATE)
in_force_national = []
expired_national = []
for pid, fm_d in all_p.items():
    fm = fm_d['fm']
    imp = fm.get('重要性', 0) or 0
    if imp < 4: continue
    if (fm.get('region') or {}).get('level') != '国家': continue
    e = eff_data.get(pid)
    if not e or not e.get('effective_date'): continue
    eff = to_date_obj(e['effective_date'])
    exp = to_date_obj(e['expires_at'])
    item = {
        'id': pid,
        'title': fm.get('title', '')[:55],
        'official': fm.get('official_number', '') or '',
        'issuer': '/'.join(fm.get('issuer', []))[:30],
        'effective_date': e['effective_date'],
        'expires_at': e['expires_at'],
        'effective_source': e['effective_source'][:80] if e['effective_source'] else '',
        'importance': imp,
        'days_in_force': (REPORT_DT - eff).days if eff and eff <= REPORT_DT else None,
        'days_until_expire': (exp - REPORT_DT).days if exp and exp >= REPORT_DT else None,
    }
    if exp and exp < REPORT_DT:
        item['status'] = 'expired'
        item['days_expired'] = (REPORT_DT - exp).days
        expired_national.append(item)
    elif eff > REPORT_DT:
        item['status'] = 'future'
    else:
        item['status'] = 'in_force'
        in_force_national.append(item)

in_force_national.sort(key=lambda x: (-x['importance'], x['effective_date']))
expired_national.sort(key=lambda x: x.get('days_expired', 0))


# ============================================================
# 5. 附录 B 主题×省份覆盖矩阵(及 march 新填空白)
# ============================================================
PROV_31 = ["北京市", "天津市", "上海市", "重庆市",
           "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省", "黑龙江省",
           "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
           "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
           "四川省", "贵州省", "云南省", "西藏自治区",
           "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区"]

THEMES = [
    ("v2g", "V2G/车网"),
    ("power_market", "电力市场"),
    ("charging_infra", "充电基建"),
    ("new_ess", "新型储能"),
    ("equipment_renewal", "设备更新"),
]

pol_entities = defaultdict(set)
with open(VAULT / "1_extracted" / "entities" / "_extractions.jsonl", encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        pol_entities[d['policy_id']].add(d['canonical_id'])

theme_coverage = {}
for theme_id, theme_zh in THEMES:
    covered_provs = set()
    for pid, ents in pol_entities.items():
        if theme_id not in ents: continue
        rname = (all_p.get(pid, {}).get('fm', {}).get('region') or {}).get('name', '')
        if rname in PROV_31:
            covered_provs.add(rname)
    blank = [p for p in PROV_31 if p not in covered_provs]
    theme_coverage[theme_zh] = {
        'covered_count': len(covered_provs),
        'blank_count': len(blank),
        'blank_provs': blank,
        'covered_provs': sorted(covered_provs),
    }


# ============================================================
# 6. § 5 省级落地证据(国家级追溯)— 窄口径 ⭐≥4 + 业务线
# ============================================================
# 用 march_detail 的 national_source 字段构建
# 窄口径:仅省/市/区级 + ⭐≥4 OR linkage 非空(从 Agent national_source 抽出的)
# Taxonomy 重命名:借鉴框架 → 补充细化, 主题对应 → 同向部署(更准确表述追溯关系)
march_list_by_id = {m['id']: m for m in march_list}

def derive_biz_line(kws):
    if any(k in kws for k in ['V2G', '车网']):
        return 'V2G/车网'
    if any(k in kws for k in ['虚拟电厂', '需求响应', '储能', '电力市场', '电力交易', '辅助服务', '现货']):
        return '储能·电力市场'
    if any(k in kws for k in ['充电', '充换电']):
        return '充电基建'
    if any(k in kws for k in ['加油', '成品油']):
        return '加油'
    if any(k in kws for k in ['设备更新', '以旧换新', '新能源汽车']):
        return '设备更新'
    return '综合'

LINKAGE_RENAME = {
    '直接落地': '直接落地',
    '借鉴框架': '补充细化',
    '主题对应': '同向部署',
    '其他': '同向部署',
}

evolution_chains = []
for d in march_detail:
    ns = d.get('national_source', {})
    if not ns: continue
    if ns.get('is_national_level_originated'):
        # 本身是国家级 — 跳过(它们是源头不是落地)
        continue
    pid = d['id']
    march_item = march_list_by_id.get(pid)
    if not march_item: continue

    linkage = ns.get('linkage', '')
    # 窄口径:⭐≥4 或 linkage 非空(Agent 抽出即非空)
    if march_item['importance'] < 4 and not linkage:
        continue

    if '直接落地' in linkage:
        raw_type = '直接落地'
    elif '借鉴框架' in linkage:
        raw_type = '借鉴框架'
    elif '主题对应' in linkage:
        raw_type = '主题对应'
    else:
        raw_type = '其他'
    linkage_type = LINKAGE_RENAME[raw_type]

    evolution_chains.append({
        'march_pid': pid,
        'march_title': march_item['title'][:50],
        'march_region': march_item['region'],
        'march_official': march_item['official'],
        'march_date': march_item['date'],
        'march_importance': march_item['importance'],
        'biz_line': derive_biz_line(march_item['biz_kws']),
        'national_source': ns.get('national_source_id_or_title', ''),
        'linkage_type': linkage_type,
        'linkage_full': linkage[:120],
        'evidence': ns.get('evidence', '')[:140],
    })

# 按重要性 + 日期排序
evolution_chains.sort(key=lambda e: (-e['march_importance'], e['march_date']))


# ============================================================
# 7. § 8 缺口/盲区警示
# ============================================================
gaps = []
# 西北 5/5 空白(部分主题)
for theme_zh, cov in theme_coverage.items():
    blank = cov['blank_provs']
    # 西北:陕甘宁青新
    nw = [p for p in blank if p in ['陕西省', '甘肃省', '青海省', '宁夏回族自治区', '新疆维吾尔自治区']]
    ne = [p for p in blank if p in ['辽宁省', '吉林省', '黑龙江省']]
    sw = [p for p in blank if p in ['四川省', '贵州省', '云南省', '西藏自治区', '重庆市']]
    if len(nw) >= 4:
        gaps.append({'theme': theme_zh, 'region': '西北 5 省', 'blank': nw, 'severity': 'high'})
    if len(ne) >= 2:
        gaps.append({'theme': theme_zh, 'region': '东北 3 省', 'blank': ne, 'severity': 'medium'})
    if len(sw) >= 3:
        gaps.append({'theme': theme_zh, 'region': '西南 5 省', 'blank': sw, 'severity': 'medium'})


# ============================================================
# 8. § 9 下月 watching list(已知 + LLM 推断)
# ============================================================
watching = [
    {
        'item': 'NDRC 1656《电力中长期市场基本规则》各省实施细则',
        'expected_window': '2026-04~Q2',
        'rationale': '1656 号文 2026-03-01 施行,各省 4 个月窗口期(已过 1 个月)。江苏 / 浙江 / 广东 仍 0 政策',
        'priority': 'A',
    },
    {
        'item': 'V2G 9 城试点扩围(第二批)',
        'expected_window': '2026-Q2',
        'rationale': '广州试点(P_2025_OTHER0858_255)首落地,扩围决策预期 Q2',
        'priority': 'A',
    },
    {
        'item': '充电统建统服 1000 个名额申报开放',
        'expected_window': '2026-Q2',
        'rationale': 'NDRC 1015《三年倍增》目标 2027 年 1000 个,2026 年应放第一批',
        'priority': 'A',
    },
    {
        'item': '十五五新型储能发展实施方案(NDRC 接续)',
        'expected_window': '2026-Q2~Q3',
        'rationale': '"十四五"新型储能方案已 2025-12-31 失效,十五五版尚未发布,政策真空期 4 个月',
        'priority': 'B',
    },
    {
        'item': '农村充电设施覆盖具体方案',
        'expected_window': '2026-Q2~Q3',
        'rationale': '国家能源局乡村振兴会议 3 月已部署"扩大农村充电覆盖",细则待出',
        'priority': 'C',
    },
    {
        'item': '上海以旧换新政策接续(20 号 / 21 号)',
        'expected_window': '2026-04',
        'rationale': '上海以旧换新细则 2026-03-31 到期,4 月起若无新政策衔接将出现真空期',
        'priority': 'A',
    },
]


# ============================================================
# Build final consolidated data
# ============================================================
data = {
    'report_date': REPORT_DATE,
    'meta': {
        'total_in_force_ge4_national': len(in_force_national),
        'total_expired_ge4_national': len(expired_national),
        'march_count': len(march_pids),
        'march_strong': sum(1 for m in march_list if m['category'] == 'strong'),
        'march_medium': sum(1 for m in march_list if m['category'] == 'medium'),
        'march_weak': sum(1 for m in march_list if m['category'] == 'weak'),
    },
    'monthly_compare': [
        {'month': m, 'count': month_count.get(m, 0), 'high_imp': month_high.get(m, 0)}
        for m in ['2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03']
    ],
    'march_list': march_list,
    'deep_dive_ids': DEEP_DIVE_IDS,
    'deep_dive_witnesses': deep_dive_witnesses,
    'in_force_national': in_force_national,
    'expired_national': expired_national,
    'theme_coverage': theme_coverage,
    'evolution_chains': evolution_chains,
    'gaps': gaps,
    'watching': watching,
    'data_health': {
        'vault_policies': len(all_p),
        'commentaries': 338,
        'entity_canonical': 88,
        'relations_total': 198,
        'crystallized_themes': 3,
        'lint_errors': 1,
        'lint_warnings': 37,
        'lint_infos': 3,
    },
}

out_path = BATCHES / "_docx_data.json"
out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(f"docx data prepared:{out_path}")
print(f"  march_list: {len(march_list)} 政策")
print(f"  in_force_national: {len(in_force_national)}")
print(f"  expired_national: {len(expired_national)}")
print(f"  evolution chains: {len(evolution_chains)}")
print(f"  gaps: {len(gaps)}")
print(f"  watching: {len(watching)}")
