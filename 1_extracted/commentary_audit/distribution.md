# Commentary Audit — Distribution Report

**Total files:** 364

## 4-Class Distribution

| Type | Count | % | Description |
|------|-------|---|-------------|
| A | 26 | 7.1% | 原创分析（高价值，留） |
| B | 89 | 24.5% | 编辑加导读的转载（中等，留但标注） |
| C | 148 | 40.7% | 纯转载（零新增量） |
| D | 101 | 27.7% | 政策解读类（官方解读） |

## Confidence Distribution

| Bucket | Count | % |
|--------|-------|---|
| high(>=0.85) | 254 | 69.8% |
| mid(0.70-0.85) | 21 | 5.8% |
| low(<0.70) | 89 | 24.5% |

## Top 10 A-type source accounts

| Rank | Source | A-count |
|------|--------|---------|
| 1 | `pdf.dfcfw.com` | 9 |
| 2 | `wri.org.cn` | 2 |
| 3 | `29629267.s21i.faiusr.com` | 2 |
| 4 | `chinaenergyportal.org` | 1 |
| 5 | `www.chinacace.org` | 1 |
| 6 | `rmi.org.cn` | 1 |
| 7 | `www.cnais.org.cn` | 1 |
| 8 | `editan.oss-cn-shanghai.aliyuncs.com` | 1 |
| 9 | `base4zgdl.xml-journal.net` | 1 |
| 10 | `theory.people.com.cn` | 1 |

## Aggressive cleanup scenarios

- If we **delete all C** (纯转载): **216** files remaining (59.3% of original)
- If we keep **only A+D** (原创+官方解读): **127** files remaining (34.9%)
- If we keep **A+B+D** (drop C only, same as above): **216** files

## Type × Confidence cross-table

| Type | high | mid | low | total |
|------|------|-----|-----|-------|
| A | 13 | 13 | 0 | 26 |
| B | 0 | 0 | 89 | 89 |
| C | 140 | 8 | 0 | 148 |
| D | 101 | 0 | 0 | 101 |

