#!/usr/bin/env node
/**
 * render_docx.js
 * 渲染 3 月月报 docx → ~/Desktop/能源政策月报-2026-03.docx
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, PageOrientation, LevelFormat,
  TabStopType, TabStopPosition,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak,
  Bookmark, InternalHyperlink, UnderlineType,
} = require('docx');

const VAULT = '/Users/shaoziyuan/Documents/Zayn Main/政策分析';
const DATA_PATH = path.join(VAULT, '_meta/march_report_batches/_docx_data.json');
const CHARTS_DIR = path.join(VAULT, '_meta/march_report_batches/charts');
const OUT_PATH = path.join(os.homedir(), 'Desktop', '能源政策月报-2026-03.docx');

const data = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));

// ============================================================
// Styling helpers
// ============================================================
const FONT = 'Microsoft YaHei';
const FONT_HEADING = 'Microsoft YaHei';

const COLOR = {
  primary: '1565C0',     // 蓝
  accent: 'C62828',      // 红(立即行动)
  warning: 'F57C00',     // 橙
  success: '2E7D32',     // 绿
  gray: '616161',
  bgLight: 'F5F5F5',
  bgBlue: 'E3F2FD',
  bgYellow: 'FFF8E1',
  bgRed: 'FFEBEE',
  bgGreen: 'E8F5E9',
};

const border = (color = 'CCCCCC', size = 1) => ({
  style: BorderStyle.SINGLE, size, color,
});
const allBorders = (color = 'CCCCCC') => ({
  top: border(color), bottom: border(color), left: border(color), right: border(color),
});

const para = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: FONT, ...opts })],
  spacing: { after: 120 },
  ...opts.paragraphProps,
});

const heading = (text, level, bookmarkId) => new Paragraph({
  heading: level,
  children: bookmarkId
    ? [new Bookmark({ id: bookmarkId, children: [new TextRun({ text, font: FONT_HEADING, bold: true })] })]
    : [new TextRun({ text, font: FONT_HEADING, bold: true })],
  spacing: { before: 280, after: 160 },
});

// TOC 条目:静态段落 + 内部锚点链接(非字段,Word 不会弹"更新引用"提示)
const tocEntry = (text, anchor) => new Paragraph({
  children: [new InternalHyperlink({
    anchor,
    children: [new TextRun({
      text,
      font: FONT,
      color: COLOR.primary,
      underline: { type: UnderlineType.SINGLE, color: COLOR.primary },
    })],
  })],
  spacing: { after: 80 },
  indent: { left: 200 },
});

const cell = (text, opts = {}) => {
  const { width = 2000, bold = false, color = '000000', bgColor = null,
          fontSize = 20, align = AlignmentType.LEFT } = opts;
  const cellOpts = {
    borders: allBorders(),
    width: { size: width, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text: text || '', font: FONT, bold, color, size: fontSize })],
    })],
  };
  if (bgColor) {
    cellOpts.shading = { fill: bgColor, type: ShadingType.CLEAR };
  }
  return new TableCell(cellOpts);
};

const tablePolicy = (headers, rows, columnWidths) => {
  return new Table({
    width: { size: columnWidths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths,
    rows: [
      new TableRow({
        children: headers.map((h, i) => cell(h, {
          width: columnWidths[i],
          bold: true,
          bgColor: COLOR.bgBlue,
          fontSize: 20,
          align: AlignmentType.CENTER,
        })),
      }),
      ...rows.map(row => new TableRow({
        children: row.map((c, i) => cell(c, { width: columnWidths[i], fontSize: 18 })),
      })),
    ],
  });
};

const imageEmbed = (filename, width, height, spacingOverride) => {
  const imgPath = path.join(CHARTS_DIR, filename);
  if (!fs.existsSync(imgPath)) {
    return para(`[图片缺失:${filename}]`, { color: COLOR.accent });
  }
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new ImageRun({
      type: 'png',
      data: fs.readFileSync(imgPath),
      transformation: { width, height },
      altText: { title: filename, description: filename, name: filename },
    })],
    spacing: spacingOverride || { before: 100, after: 100 },
  });
};

// ============================================================
// 数据预处理
// ============================================================
const RED = '[趁早行动]';
const YELLOW = '[研究 / 跟进]';
const GREEN = '[跟踪]';

// ⭐5 = 立即行动 / ⭐4 = 研究 跟进 / ⭐3 = 跟踪 / <3 = 关注
const trafficLight = (imp) => imp >= 5 ? RED : (imp >= 4 ? YELLOW : (imp === 3 ? GREEN : '[关注]'));

const trafficLightColor = (imp) => imp >= 5 ? COLOR.accent : (imp >= 4 ? COLOR.warning : (imp === 3 ? COLOR.success : COLOR.gray));
const trafficLightBg = (imp) => imp >= 5 ? COLOR.bgRed : (imp >= 4 ? COLOR.bgYellow : (imp === 3 ? COLOR.bgGreen : COLOR.bgLight));

// 重要性显示(纯文本)
const impText = (n) => `${n}/5 重要性`;

// ============================================================
// 章节构造
// ============================================================
const children = [];

// ============== 封面 ==============
children.push(
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: '能源政策月报', font: FONT_HEADING, bold: true, size: 64 })],
    spacing: { before: 2400, after: 400 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: '2026 年 3 月', font: FONT_HEADING, size: 48 })],
    spacing: { after: 1600 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: '报告日期:2026-03-31', font: FONT, size: 24 })],
    spacing: { after: 100 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({
      text: `本月入库政策 ${data.meta.march_count} 篇 · 强相关 ${data.meta.march_strong} · 中相关 ${data.meta.march_medium} · 弱/无相关 ${data.meta.march_weak}`,
      font: FONT, size: 22, color: COLOR.gray,
    })],
  }),
  new Paragraph({ children: [new PageBreak()] })
);

// ============== TOC(静态段落 + 内部锚点,非字段)==============
children.push(
  heading('目录', HeadingLevel.HEADING_1),
  tocEntry('§ 1 月度速览', 's1'),
  tocEntry('§ 2 决策卡片', 's2'),
  tocEntry('§ 3 政策全列表', 's3'),
  tocEntry('§ 4 重点解读 — 国家级新政', 's4'),
  tocEntry('§ 5 省级落地证据(国家级追溯)', 's5'),
  tocEntry('§ 6 机会-风险 2×2 矩阵', 's6'),
  tocEntry('§ 7 缺口 / 盲区警示', 's7'),
  tocEntry('§ 8 下月 watching list', 's8'),
  tocEntry('附录 A · 国家级重要政策生效周期', 'sa'),
  tocEntry('附录 B · 重要政策各省覆盖度', 'sb'),
  new Paragraph({ children: [new PageBreak()] })
);

// ============== § 1 月度速览 ==============
children.push(
  heading('§ 1 月度速览', HeadingLevel.HEADING_1, 's1'),
  para('1.1 数字一览', { bold: true, size: 24 }),
);

const monthly = data.monthly_compare;
children.push(tablePolicy(
  ['月份', '入库政策数', '重要政策(⭐≥4)'],
  monthly.map(m => [m.month, String(m.count), String(m.high_imp)]),
  [3000, 3000, 3000],
));

children.push(
  para('', { size: 18 }),
  imageEmbed('05_monthly_compare.png', 600, 300),
  para('', { size: 18 }),
  para('1.2 本月最重要 2 件事', { bold: true, size: 24 }),
);

[
  ['一 · 国家级最高规格政策密集落地', '本月《2026 年政府工作报告》(3-5)+《十五五规划纲要》(3-13)同期出台,与政府工作报告中"新型储能装机超 1.3 亿千瓦、非化石能源占比 21.7%、单位 GDP 碳强度累计降 17%"的量化承诺联动,为公司三大业务(加油 / 充电 / 电力,后者含储能·V2G·电力交易)提供 5 年顶层政策授权。'],
  ['二 · 国家级动向的省级落地', '山东省虚拟电厂高质量发展方案(3-27)是 NDRC 357 号《虚拟电厂指导意见》之后省级第 2 个 VPP 专项(前序:上海《用户侧虚拟电厂建设实施方案 2025-2027 年》沪经信运〔2025〕407 号 2025-06-19),2027 年 200 万 kW / 2030 年 400 万 kW 量化目标具体;宁夏年度充电方案(3-20)是 NDRC 1015《三年倍增》在西北 5 省空白首破。两条省级动向均属"国家级文件落地节奏"的关键时点信号。'],
].forEach(([h, body]) => {
  children.push(
    para(h, { bold: true, size: 22, color: COLOR.primary }),
    para(body, { size: 20 }),
    para('', { size: 14 }),
  );
});

// ============== § 2 决策卡片(仅 strong ⭐≥4)==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 2 决策卡片', HeadingLevel.HEADING_1, 's2'),
  para('本月 11 篇政策中,重要性 ⭐≥4 且业务直接相关的 4 篇 — 决策层第一时间需要做判断。', { size: 20, italics: true, color: COLOR.gray }),
  para('其他 5 篇中相关 + 2 篇弱相关详见 § 3 全列表。', { size: 18, italics: true, color: COLOR.gray }),
  para('', { size: 12 }),
);

const strongOnly = data.march_list.filter(m => m.category === 'strong');

strongOnly.forEach((p, i) => {
  const light = trafficLight(p.importance);

  children.push(
    new Paragraph({
      children: [new TextRun({
        text: `卡片 ${i + 1} · ${light}`,
        font: FONT, bold: true, size: 24,
        color: trafficLightColor(p.importance),
      })],
      spacing: { before: 280, after: 100 },
    }),
    para(`政策:${p.title}`, { bold: true, size: 22 }),
    para(`日期:${p.date} · 发文:${p.issuer.join(' / ')} · 区域:${p.region} · 重要性:${impText(p.importance)}${p.official ? ' · ' + p.official : ''}`,
        { size: 18, color: COLOR.gray }),
    para('', { size: 10 }),
    para(`政策核心:${p.core_one_line}`, { size: 20 }),
    para(`公司影响:${p.didi_impact_one_line}`, { size: 20 }),
  );

  if (p.action_recommendations && p.action_recommendations.length > 0) {
    children.push(para(`行动建议(${p.action_recommendations.length} 条):`, { size: 20, bold: true }));
    p.action_recommendations.slice(0, 3).forEach(act => {
      children.push(new Paragraph({
        children: [new TextRun({ text: `  · ${act}`, font: FONT, size: 18 })],
        indent: { left: 200 },
        spacing: { after: 60 },
      }));
    });
  }

  if (p.national_source && p.national_source.national_source_id_or_title) {
    children.push(para(`国家级源头:${p.national_source.national_source_id_or_title}`,
                      { size: 18, color: COLOR.primary, italics: true }));
  }

  children.push(new Paragraph({
    children: [new TextRun({ text: '', font: FONT })],
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'BBBBBB', space: 1 } },
    spacing: { before: 100, after: 200 },
  }));
});

// ============== § 3 政策全列表 ==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 3 政策全列表', HeadingLevel.HEADING_1, 's3'),
  imageEmbed('06_relevance_pie.png', 480, 360),
  para('', { size: 14 }),
);

// 强相关
children.push(heading('3.1 强相关 ⭐≥4 + 业务命中', HeadingLevel.HEADING_2));
const strongRows = data.march_list.filter(m => m.category === 'strong').map(m => [
  m.date, m.region, `⭐${m.importance}`, m.title.substring(0, 30),
  m.biz_kws.slice(0, 4).join('/')
]);
children.push(tablePolicy(
  ['发布日', '区域', '⭐', '标题', '业务命中'],
  strongRows,
  [1200, 1500, 800, 4000, 1500],
));

// 中相关
children.push(
  para('', { size: 14 }),
  heading('3.2 中相关 ⭐3 + 业务命中', HeadingLevel.HEADING_2),
);
const mediumRows = data.march_list.filter(m => m.category === 'medium').map(m => [
  m.date, m.region, `⭐${m.importance}`, m.title.substring(0, 30),
  m.biz_kws.slice(0, 4).join('/')
]);
children.push(tablePolicy(
  ['发布日', '区域', '⭐', '标题', '业务命中'],
  mediumRows,
  [1200, 1500, 800, 4000, 1500],
));

// 弱相关
children.push(
  para('', { size: 14 }),
  heading('3.3 弱相关 / 业务无关', HeadingLevel.HEADING_2),
);
const weakRows = data.march_list.filter(m => m.category === 'weak').map(m => [
  m.date, m.region, `⭐${m.importance}`, m.title.substring(0, 35), m.biz_kws.length ? '弱命中' : '无命中'
]);
children.push(tablePolicy(
  ['发布日', '区域', '⭐', '标题', '相关性'],
  weakRows,
  [1200, 1500, 800, 4000, 1500],
));

// ============== § 4 重点解读 — 国家级新政深度解读 ==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 4 重点解读 — 国家级新政', HeadingLevel.HEADING_1, 's4'),
  para('本月 3 篇国家级最高规格新政详读:政策核心、对公司三大业务影响、行动建议。',
      { italics: true, size: 20, color: COLOR.gray }),
);

const witnessesData = data.deep_dive_witnesses || {};

data.deep_dive_ids.forEach((pid, idx) => {
  const p = data.march_list.find(x => x.id === pid);
  if (!p) return;

  children.push(
    heading(`4.${idx + 1} 《${p.title}》`, HeadingLevel.HEADING_2),
    para(`日期:${p.date} · 发文:${p.issuer.join(' / ')} · 重要性:${impText(p.importance)}${p.official ? ' · ' + p.official : ''}`,
        { size: 18, color: COLOR.gray }),
    para('', { size: 10 }),

    para('一 · 政策核心', { bold: true, size: 22, color: COLOR.primary }),
    para(p.summary_2_3 || p.core_one_line || '', { size: 20 }),
    para('', { size: 10 }),

    para('二 · 对公司三大业务影响', { bold: true, size: 22, color: COLOR.primary }),
  );

  const bi = p.biz_impact || {};
  // 公司三大业务:加油 / 充电 / 电力(后者含储能·V2G·电力交易)
  // 乡村是关注方向(非业务线),如 Agent 抽出 '乡村' 字段则单独展示
  const labels = {
    '加油': '加油业务',
    '充电': '充电业务',
    '电力_储能_V2G_交易': '电力业务(储能 / V2G / 电力交易)',
  };
  ['加油', '充电', '电力_储能_V2G_交易'].forEach(k => {
    const v = bi[k];
    if (v && v !== '无直接影响') {
      children.push(para(`· ${labels[k]}:${v}`, { size: 20 }));
    }
  });
  // 乡村能源单独展示为关注方向(非业务线)
  const ruralImpact = bi['乡村'];
  if (ruralImpact && ruralImpact !== '无直接影响') {
    children.push(para(`· 乡村能源(关注方向,非业务线):${ruralImpact}`, { size: 20, color: COLOR.gray }));
  }

  if (p.action_recommendations && p.action_recommendations.length > 0) {
    children.push(
      para('', { size: 8 }),
      para('三 · 行动建议', { bold: true, size: 22, color: COLOR.primary }),
    );
    p.action_recommendations.forEach(act => {
      children.push(new Paragraph({
        children: [new TextRun({ text: `· ${act}`, font: FONT, size: 20 })],
        indent: { left: 200 },
        spacing: { after: 80 },
      }));
    });
  }

  // 国家级溯源(本身)
  if (p.national_source && p.national_source.is_national_level_originated) {
    children.push(
      para('', { size: 8 }),
      para('四 · 政策定位', { bold: true, size: 22, color: COLOR.primary }),
      para(`本政策为国家级最高规格文件本身。${p.national_source.linkage || ''}`,
          { size: 18, italics: true, color: COLOR.gray }),
    );
  }

  // 注:"省级落地证据"块已删除(用户反馈 — 放在每篇国家级新政后不合理,后续讨论放置位置)
  children.push(para('', { size: 14 }));
});

// ============== § 5 省级落地证据(国家级追溯)==============
// 注:省级政策起草周期通常 6-12 月,与本月国家级新政(政府工作报告 / 十五五 / 乡村振兴会议)
//     属"同源并行"而非"派生因果"。下表追溯到的国家级源头,多为 2023-2025 年早期文件路径。
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 5 省级落地证据(国家级追溯)', HeadingLevel.HEADING_1, 's5'),
  para('本月省/市级政策追溯到的国家级源头政策——多数源自 2023-2025 年早期国家级路径,而非本月新政。本月 3 篇国家级新政(政府工作报告 / 十五五 / 乡村振兴会议)与省级政策属"同源并行",非"派生因果":省级专项起草周期 6-12 月,物理上不可能响应同月国家级。下表呈现追溯链条与 linkage 类型(直接落地 / 补充细化 / 同向部署)。',
      { size: 20 }),
  imageEmbed('04_evolution_chain.png', 540, 293, { before: 280, after: 280 }),
  para('', { size: 14 }),
  heading('5.1 ⭐≥4 省级政策 → 国家级源头', HeadingLevel.HEADING_2),
);

const evoRows = data.evolution_chains.map(e => [
  `${e.march_region} ${e.march_title.substring(0, 18)}`,
  e.march_official ? `${e.march_official} · ${e.march_date}` : e.march_date,
  e.biz_line || '综合',
  e.national_source.substring(0, 35),
  e.linkage_type || '同向部署',
]);
children.push(tablePolicy(
  ['省级政策', '文号·日期', '业务线', '国家级源头', 'linkage 类型'],
  evoRows,
  [2200, 2200, 1300, 2300, 1000],
));

children.push(
  para('', { size: 12 }),
  para('linkage 类型说明:直接落地 = 省级文本直接引用国家级文号;补充细化 = 主题对齐且条款扩展(地方实施细则常见);同向部署 = 主题、目标、节奏与国家级路径吻合,无显式引用。',
      { size: 16, italics: true, color: COLOR.gray }),
);

// (原 § 6 舆论温度计已删除 — TODO: 评论发酵后重写)

// ============== § 6 机会-风险 2x2(原 § 7)==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 6 机会-风险 2×2 矩阵', HeadingLevel.HEADING_1, 's6'),
  para('11 篇 3 月政策按"业务相关性 × 行动窗口"两维分布。', { size: 20 }),
  imageEmbed('02_2x2_matrix.png', 540, 386, { before: 280, after: 280 }),
);

// ============== § 7 缺口/盲区(原 § 8)==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 7 缺口 / 盲区警示', HeadingLevel.HEADING_1, 's7'),
  imageEmbed('03_regional_heatmap.png', 800, 220),
  para('', { size: 14 }),
  heading('7.1 主题 × 31 省覆盖概览', HeadingLevel.HEADING_2),
);

const covRows = Object.entries(data.theme_coverage).map(([theme, c]) => [
  theme,
  `${c.covered_count}/31`,
  `${Math.round(c.covered_count / 31 * 100)}%`,
  c.blank_provs.slice(0, 5).map(p => p.replace(/[省市区自治]+$/, '')).join('/'),
]);
children.push(tablePolicy(
  ['主题', '覆盖省份数', '覆盖率', '空白(前 5)'],
  covRows,
  [2200, 1500, 1200, 4100],
));

children.push(
  para('', { size: 14 }),
  heading('7.2 本月新填空白', HeadingLevel.HEADING_2),
  para('· 充电基建:宁夏首破(西北 5/5 空白省份之一)— 但毗邻甘青陕蒙仍空白', { size: 20, bold: true }),
  para('· 电力市场 / 虚拟电厂:山东加深覆盖(NDRC 357 后省级第 2 个 VPP 专项,前序:上海 沪经信运〔2025〕407 号 2025-06)', { size: 20, bold: true }),
  para('', { size: 14 }),
  heading('7.3 持续盲区(高严重度)', HeadingLevel.HEADING_2),
);

const gapHigh = data.gaps.filter(g => g.severity === 'high').slice(0, 5);
gapHigh.forEach(g => {
  children.push(para(`· [${g.theme}] ${g.region}:${g.blank.map(p => p.replace(/[省市区自治]+$/, '')).join(' / ')}`,
                     { size: 20, color: COLOR.accent, bold: true }));
});

// ============== § 8 下月 watching list(原 § 9)==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('§ 8 下月 watching list', HeadingLevel.HEADING_1, 's8'),
  para('基于政策窗口期 + 历史关系网推断 4 月可能出台或落地的政策。', { italics: true, color: COLOR.gray }),
);

const watchRows = data.watching.map(w => [w.priority, w.item.substring(0, 35), w.expected_window, w.rationale.substring(0, 60)]);
children.push(tablePolicy(
  ['优先级', '关注事项', '预期窗口', '理由'],
  watchRows,
  [1000, 3500, 1500, 3000],
));

// (原 § 9 数据健康度小卡已删 — 用户反馈:对决策层无价值)

// ============== 附录 A timeline ==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('附录 A · 国家级重要政策生效周期', HeadingLevel.HEADING_1, 'sa'),
  para(`报告日 2026-03-31 视角:国家级 ⭐≥4 政策中,**${data.meta.total_in_force_ge4_national}** 篇仍生效,**${data.meta.total_expired_ge4_national}** 篇已失效(可能进入"政策真空期")。`,
      { size: 20 }),
  imageEmbed('01_timeline.png', 800, 1200),
  para('', { size: 14 }),
  heading('A1 已失效政策(政策真空期警示)', HeadingLevel.HEADING_2),
);

const expRows = data.expired_national.slice(0, 12).map(e => [
  e.title.substring(0, 30), e.effective_date || '?', e.expires_at || '?',
  String(e.days_expired || 0) + ' 天'
]);
children.push(tablePolicy(
  ['政策标题', '生效日', '失效日', '已过期'],
  expRows,
  [4000, 1500, 1500, 2000],
));

// ============== 附录 B 区域覆盖 ==============
children.push(
  new Paragraph({ children: [new PageBreak()] }),
  heading('附录 B · 重要政策各省覆盖度', HeadingLevel.HEADING_1, 'sb'),
  para('5 大主题 × 31 省级行政区覆盖矩阵(单元格 = 该主题在该省的政策数量)。', { size: 20 }),
  imageEmbed('03_regional_heatmap.png', 800, 220),
  para('', { size: 14 }),
  heading('B.1 各主题覆盖详情', HeadingLevel.HEADING_2),
);

Object.entries(data.theme_coverage).forEach(([theme, c]) => {
  children.push(
    para(theme, { bold: true, size: 22, color: COLOR.primary }),
    para(`已覆盖(${c.covered_count}):${c.covered_provs.map(p => p.replace(/[省市区自治]+$/, '')).join(' / ')}`,
        { size: 18 }),
    para(`空白(${c.blank_count}):${c.blank_provs.map(p => p.replace(/[省市区自治]+$/, '')).join(' / ')}`,
        { size: 18, color: COLOR.gray }),
    para('', { size: 10 }),
  );
});

children.push(
  heading('B.2 本月新政在 31 省的扩散预期', HeadingLevel.HEADING_2),
  para('▸ 山东 VPP → 预计跟随省份:广东 / 江苏 / 浙江(经济发达 + 电力交易市场成熟)',
      { size: 20 }),
  para('▸ 宁夏充电 → 预计跟随省份:陕西 / 甘肃 / 青海(西北邻省,产业空白接续)',
      { size: 20 }),
);

// (原附录 C 数据出处与方法论已删 — 用户反馈:对决策层无价值,工具尾注亦删)

// ============================================================
// 组装文档
// ============================================================
const doc = new Document({
  creator: 'Claude (Anthropic) - policy-watch L3',
  title: '能源政策月报 2026-03',
  description: '公司决策层 月度政策动向',
  styles: {
    default: {
      document: { run: { font: FONT, size: 22 } },
    },
    paragraphStyles: [
      {
        id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: FONT_HEADING, color: COLOR.primary },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 },
      },
      {
        id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: FONT_HEADING, color: COLOR.primary },
        paragraph: { spacing: { before: 280, after: 150 }, outlineLevel: 1 },
      },
      {
        id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: FONT_HEADING, color: COLOR.gray },
        paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 2 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },  // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: '能源政策月报 · 2026-03', font: FONT, size: 18, color: COLOR.gray })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: 'Page ', font: FONT, size: 18 }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 }),
            new TextRun({ text: ' · 公司', font: FONT, size: 18, color: COLOR.gray }),
          ],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT_PATH, buf);
  const stats = fs.statSync(OUT_PATH);
  console.log(`月报已生成:`);
  console.log(`   ${OUT_PATH}`);
  console.log(`   ${(stats.size / 1024).toFixed(1)} KB`);
}).catch(err => {
  console.error('生成失败:', err);
  process.exit(1);
});
