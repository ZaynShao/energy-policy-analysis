# Weekly Audit — 2026-05-07

- 跑时: 2026-05-07T13:46:29+08:00
- 主题×省矩阵: 257/257 cells (100.0%)
- citation gap: 1456 篇
- relations: 664 政策 / 1148 边 / 132 isolated

## 各 audit 子脚本结果
- [✓] coverage
      TSV 矩阵 -> /Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/audit_2026-05-06/coverage_matrix.tsv
      摘要 -> /Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/audit_2026-05-06/coverage_baseline.md
      matrix.json -> /Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/audit_2026-05-06/coverage_matrix.json
- [✓] official_number
      注: 当前 vault 单机构单年命中 1-3 篇是常态,'缺号'更多反映
      我们没收 vs 真没发,需要后续 Tavily site:filter 验证
- [✓] citation
      === 引用反扫审计完成 ===
      摘要 -> /Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/audit_2026-05-06/citation_gaps.md
      缺口清单 -> /Users/shaoziyuan/Documents/Zayn Main/政策分析/_meta/audit_2026-05-06/citation_gaps.json

## 详细输出
- coverage_baseline: `_meta/audit_2026-05-06/coverage_baseline.md`
- official_number: `_meta/audit_2026-05-06/official_number_audit.md`
- citation_gaps: `_meta/audit_2026-05-06/citation_gaps.md`

## 阈值告警
跑 `python3 _meta/scripts/audit_alert.py` 比较与上周 state 的差异。