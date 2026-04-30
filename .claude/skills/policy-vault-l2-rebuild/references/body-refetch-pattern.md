# Body Refetch Pattern(PDF 乱码重抓协议)

适用场景:发现 raw body 是 PDF 二进制 / HTML 乱码 / 抓取失败的非可读内容。

## 检测口径(决定哪些政策要重抓)

```python
# 见 vault 内已写的 _low_quality_audit.py 模式
# 关键指标(任一命中即视为低质):
1. body 长度 < 100 字符  → "body_too_short"
2. body 含 "%PDF" / "endobj" / "endstream" / "<</Type" 等 PDF 二进制特征
3. 可读字符占比 < 0.85
   (中文 + ASCII printable + 常见全角符号 / 总字符数)
```

## 重抓 7 步流程

### Step 1: 找原 source URL

读 raw frontmatter 的 `provenance.url` — 90% 政策有此字段。如无,需 WebSearch 找官方源。

### Step 2: 下载

```bash
curl -sS -L --max-time 60 -o /tmp/refetch.pdf "<URL>"
file /tmp/refetch.pdf  # 验证类型
```

ndrc.gov.cn / nea.gov.cn / gov.cn 在国内直接通,无需代理(本会话验证过)。

### Step 3: 解析

| 文件类型 | 工具 |
|---|---|
| `.pdf` | `pdfplumber`(`pip3 install pdfplumber`) |
| `.doc`(Composite Document File V2) | macOS 自带 `textutil -convert txt input.doc -output output.txt` |
| `.docx` | `pandoc` 或 `python-docx` |
| HTML | `trafilatura.extract()` 或 `bs4.BeautifulSoup` |

PDF 解析示例:
```python
import pdfplumber
with pdfplumber.open('/tmp/refetch.pdf') as pdf:
    text = '\n\n'.join((p.extract_text() or '') for p in pdf.pages)
```

### Step 4: 校验提取质量

- 必须含 title 关键词
- 必须含完整章节("一、""二、""三、"...)
- 字符数 ≥ 1000(短政策可放宽到 500)
- 不应有 PDF binary 残留

如校验失败 → 换工具(如 textutil 失败试 pandoc)。

### Step 5: 备份原 raw

```bash
mkdir -p 0_raw/_archive/policies
cp "0_raw/policies/<原文件>.md" "0_raw/_archive/policies/<原文件>__pre_pdfreextract_<timestamp>.md"
```

**严禁省略备份** — 这是回滚保险。

### Step 6: 替换 body + 加 audit 字段

不动 frontmatter 的 fact 字段(id/title/official_number/issuer/date/region/aliases)。
只:
- 在 `provenance` 下加:
  ```yaml
  provenance:
    # ...原字段全保留
    body_refetched_at: '2026-04-30T10:28:33+08:00'
    body_refetched_method: pdfplumber  # 或 textutil / trafilatura
    body_refetched_from: '<URL>'
    body_pre_refetch_len: 242370       # 被替换的乱码长度
  ```
- body 切分:保留 `# title` + metadata 块 + `## 政策原文` 标题(以及之前的内容),替换 `## 政策原文` 之后的全部内容为新提取文本

如果原 body 没有 `## 政策原文` marker → 末尾追加 `\n\n## 政策原文(重抓)\n\n<新文本>`。

### Step 7: 后续(走 trigger A pid_change)

body 变了,5C 派生 + 关系层都要重抽:

```bash
python3 _meta/scripts/rebuild_l2.py prepare --trigger pid_change --pids P_xxx,P_yyy,...
# 派 2 subagent
python3 _meta/scripts/rebuild_l2.py apply --stage 5c
python3 _meta/scripts/rebuild_l2.py apply --stage rel
python3 _meta/scripts/rebuild_l2.py deterministic --scope post-llm
```

## title-body 错配 audit

重抓后 5C subagent 应自动检查 body 是否与 title 主题一致。如不一致(本会话 P_2024_TJ_01010970 案):
- subagent 在 summary 字段标注 "标题与正文不符,正文为 X"
- D1 给低分(1-2)
- 流程不阻塞,但记入 backlog 待人工 audit

## LLM Wiki §1 合规性论证

§1 说"raw 一旦入库不再编辑",唯一例外是"重抓重入"。本协议:
- ✓ pid 不变 → 关系层 / 反链 / business_view 不断
- ✓ frontmatter fact 字段不动
- ✓ body 替换是修复抓取 bug,不是派生倒灌
- ✓ audit 字段完整(`body_refetched_*`)留痕
- ✓ 备份保留 → 可回滚

属合规的"轻量重抓重入"。

## 本会话案例(2026-04-30)

14 篇 PDF 乱码:
- 11 直接 .pdf url → pdfplumber
- 2 doc(慈溪市 / 重庆市城市更新) → textutil
- 1 国家能源局长 hash url → 实际 PDF → pdfplumber

成功 14/14。后续 5C 重跑出 11 D1≥3、3 D1<2(含 1 篇 title-body 错配)。derives_from 增 12 边。
