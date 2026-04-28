# conflicts_with 第一轮判定报告

- 候选对: 161 (≥3 共享 tag + 时差 ≤1y + 同 region_level + 不在演进链)
- LLM 判定: 4 subagent 并发

## 类别分布

- complement: 152
- noise: 1
- aligns: 8

## 关键发现:数据稀疏不等于无冲突

4 个 subagent 一致诊断:**body_500 信息密度不足以判 conflicts**。
原因分析:
- 政策正式文本不会显式承认互相冲突(部委间)
- 真正的冲突表现在执行层面(如跨省补贴标准差异)
- 或体现在 commentary 评论的 critical stance 中

## 留下一轮 P1

1. **conflicts_with 二轮**:候选扩到 body_3000,LLM 重判 161 候选
2. **commentary stance 反推路径**:从 opinions/<id>.md 的 critical stances 聚合,看哪些"分歧议题"指向真冲突
3. 8 aligns 候选可作为 aligns_with 后续抽取的种子