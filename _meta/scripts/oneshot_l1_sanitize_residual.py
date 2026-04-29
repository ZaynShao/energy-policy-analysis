#!/usr/bin/env python3
"""
oneshot_l1_sanitize_residual.py — L1.2 残留 7 篇精细净化(2026-04-29 一次性)

oneshot_l1_sanitize.py 跑完后剩余 7 篇含「滴滴」,分两类:
  A 类(5 篇): ## 摘要 段尾业务关联句(「,与滴滴...」「。与滴滴...」)
  B 类(2 篇): 整段业务侧分析(十五五规划「滴滴四大业务战略地位映射」、乡村振兴「跟进建议」)

跑完即删脚本。
"""

import re
from pathlib import Path

VAULT = Path("/Users/shaoziyuan/Documents/Zayn Main/政策分析")
RAW = VAULT / "0_raw" / "policies"


def strip_didi_sentences_in_section(text: str, section_header: str) -> str:
    """在指定 section(以 `## 名称` 开头到下一个 ## 之前)内,删除含「滴滴」的句子。
    句子边界:中文句号 。 / 英文句号 . / 中文分号 ; / 中文逗号 , / 段落结尾。"""
    pat = re.compile(rf"^{re.escape(section_header)}\s*$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text
    sec_start = m.end()
    next_h2 = re.compile(r"^## ", re.MULTILINE).search(text, sec_start)
    sec_end = next_h2.start() if next_h2 else len(text)
    section = text[sec_start:sec_end]

    # 删除含「滴滴」的句子(以 。 ; , ! ? 分句,保留分隔符前的非滴滴句)
    def clean_paragraph(para: str) -> str:
        sentences = re.split(r"([。;,!?])", para)
        out = []
        i = 0
        while i < len(sentences):
            s = sentences[i]
            sep = sentences[i + 1] if i + 1 < len(sentences) else ""
            if "滴滴" in s:
                pass
            else:
                out.append(s + sep)
            i += 2
        return "".join(out).rstrip(",;。 \n")

    cleaned = "\n\n".join(clean_paragraph(p) for p in section.split("\n\n"))
    return text[:sec_start] + cleaned + ("\n\n" if not cleaned.endswith("\n") else "") + text[sec_end:]


def cut_h3_subsection(text: str, h3_title: str) -> str:
    """删整个 `### 标题` 子段,到下一个 ## 或 ### 之前。"""
    pat = re.compile(rf"^### {re.escape(h3_title)}.*?$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text
    start = m.start()
    next_h = re.compile(r"^(### |## )", re.MULTILINE).search(text, m.end())
    end = next_h.start() if next_h else len(text)
    return text[:start] + text[end:]


def cut_h2_section(text: str, h2_title: str) -> str:
    """删整个 `## 标题` 段,到下一个 ## 之前。"""
    pat = re.compile(rf"^## {re.escape(h2_title)}.*?$", re.MULTILINE)
    m = pat.search(text)
    if not m:
        return text
    start = m.start()
    next_h2 = re.compile(r"^## ", re.MULTILINE).search(text, m.end())
    end = next_h2.start() if next_h2 else len(text)
    return text[:start] + text[end:]


def remove_table_column(text: str, header_keyword: str) -> str:
    """删除 markdown 表格中含 header_keyword 的列(简单实现:逐行操作 | 分隔)。"""
    lines = text.split("\n")
    out = []
    in_table = False
    drop_idx = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            cells = [c for c in line.split("|")]
            if not in_table:
                # 表头行
                in_table = True
                for i, c in enumerate(cells):
                    if header_keyword in c:
                        drop_idx = i
                        break
                if drop_idx is None:
                    in_table = False
                    out.append(line)
                    continue
            if drop_idx is not None and len(cells) > drop_idx:
                cells.pop(drop_idx)
                out.append("|".join(cells))
            else:
                out.append(line)
        else:
            in_table = False
            drop_idx = None
            out.append(line)
    return "\n".join(out)


# A 类: 5 篇,## 摘要 段去滴滴句
A_FILES = [
    "【上海市关于贯彻落实第二轮中央生态环境保护督察反馈意见整改情况的报告】-上海市委、市政府-45fa.md",
    "【上海市崇明区国家生态文明建设示范区规划(2024—2035年)(沪崇府发〔2024〕41号)】-上海市崇明区人民政府-552f.md",
    "【加快推动小水电绿色转型高质量发展的指导意见】-国家林业和草原局(转载)-4377.md",
    "【北京市绿色低碳发展国民教育体系建设实施方案】-北京市教育委员会-2c7b.md",
    "【涪陵区综合能源站发展规划(2023—2030年)】-重庆市涪陵区人民政府-6819.md",
]

# B 类: 2 篇,整段业务侧分析删
B_15_5 = "【中华人民共和国国民经济和社会发展第十五个五年规划纲要(2026-2030年)】-全国人民代表大会-2f88.md"
B_RURAL = "【国家能源局乡村振兴工作领导小组2026年第一次会议】-国家能源局-ed54.md"


def main():
    # A 类
    for fname in A_FILES:
        p = RAW / fname
        if not p.exists():
            print(f"[skip] {fname} not found")
            continue
        text = p.read_text(encoding="utf-8")
        new_text = strip_didi_sentences_in_section(text, "## 摘要")
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            print(f"[A] {fname[:50]}... → 摘要去滴滴句")
        else:
            print(f"[A] {fname[:50]}... → 无变更(摘要里没匹配到)")

    # B 类 1: 十五五规划
    p = RAW / B_15_5
    if p.exists():
        text = p.read_text(encoding="utf-8")
        text = cut_h3_subsection(text, "滴滴四大业务的战略地位映射")
        text = remove_table_column(text, "与滴滴关联度")
        p.write_text(text, encoding="utf-8")
        print(f"[B] 十五五规划 → 删「滴滴四大业务战略地位映射」子段 + 表格列")

    # B 类 2: 乡村振兴会议
    p = RAW / B_RURAL
    if p.exists():
        text = p.read_text(encoding="utf-8")
        text = cut_h2_section(text, "跟进建议")
        text = remove_table_column(text, "滴滴关联")
        p.write_text(text, encoding="utf-8")
        print(f"[B] 乡村振兴 → 删「## 跟进建议」段 + 表格列")


if __name__ == "__main__":
    main()
