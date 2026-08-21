---
title: 马斯克要用 Grok 4.6 挤进「御三家」
source_account: APPSO
source_url: https://mp.weixin.qq.com/s/jWszyNS-_huPvhi2wHhd-Q
date_published: '2026-08-14'
fetched_at: '2026-08-16T07:31:42+08:00'
source: wewe-rss
---

# 马斯克要用 Grok 4.6 挤进「御三家」

谁敢数数马斯克这两天发了多少推？
昨天的主题是 Grok Bot，今天是 Grok 4.6。
他是铁了心要做 Top 3，哦不，是要做就做 Number 1。
距离上一代模型 Grok 4.5 发布仅仅过去了 35 天，马斯克此时便已经预告大家 Grok 4.7 将超过当前所有模型了。
我们先别信，先来一起看看 Grok 4.6 究竟表现如何。
xAI 对 Grok 4.6 的官方定位，是一个能够胜任「研究一个话题、分析信息、跨代码库协作、把一个想法变成一个可运行的应用」。
这类需要持续推进多个步骤的任务的模型——瞄准的是需要多轮推理、状态保持和工具协调的真实工作场景。
在 Artificial Analysis Intelligence Index 上，Grok 4.6 拿到 61 分，全球第三——前面是 Claude Opus 5（63）和 Claude Fable 5（62），与 GPT-5.6 Sol 并列，身后紧跟 Kimi K3。
代际对比上，Grok 4.6 比上一代 4.5 涨了 5 分，比一个多月前的 Grok 4.3 涨了整整 23 分。Artificial Analysis 对此评价，xAI 重回前沿梯队，「只落后于 Anthropic」。
https://x.com/HarshithLucky3/status/2087590866848526447
知识工作维度上，Grok 4.6 拿到 1753 分，小幅领先 Claude Fable 5 的 1741 分和 GPT-5.6 Sol 的 1728 分，在同级竞品中位居榜首。
这说明模型在复杂知识任务，例如长文档分析、跨领域问答、多步推理中综合表现最佳。
法律与复杂专业推理方向，Harvey LAB 的数据更夸张些：Grok 4.6 拿到 15.8%，大幅领先 Fable 5 Max 的 11.3%，而 GPT-5.6 仅 2.5%。
这意味着 Grok 4.6 对专业领域的深度理解和多步推导能力领先。
多轮工具调用方面，τ³-Banking 模拟客服结合工具调用的真实业务场景，Grok 4.6 以 50.7% 拿到全场第二，仅次于 Qwen3.8 Max 的 51.3%。长程知识工作场景的 AA-Briefcase Elo 为 1577，处于 Fable 5 档位，落后于 Opus 5 系列。
Cursor CEO Michael Truell 在发布第一时间给出背书，称这个模型在「高难度任务和知识工作上明显更强，把 Opus 级智能和低成本高速度结合在了一起」。
有开发者调用 Grok 4.6 的工具链，完成了一个河流演变过程的五阶段动态演练——从早期原始生态河流，到水运贸易、工业时代改造、现代滨水区设计，直至最终的生态恢复阶段。
https://x.com/techartist_/status/2087584847212798139
整个多步骤任务中，模型展现出极强的长程状态保持与工具链调度能力，中途没有出现上下文漂移或工具调用中断。
SpaceX 今年早些时候以约 600 亿美元完成了对 Cursor 的收购，而这次模型迭代，Cursor 的数据价值首次被系统性地注入训练流程。
具体来说，Grok 4.6 的 SFT 阶段使用了 Grok 4.5 重新生成的轨迹数据，覆盖 STEM、软件工程和知识工作等多个领域，并通过模型自检机制过滤有问题的训练样本。
换句话说，Cursor 积累的海量真实开发者调试数据，这次正式进了训练管线。
效果立竿见影：Grok 4.6 在 DeepSWE v1.1（考察模型在真实软件工程任务中的代码生成与调试能力）上，从 4.5 的 54% 大幅跳到 65.9%，提升近 12 个百分点；APEX-Agents（测试多步骤 Agent 任务完成率）从 47.1% 升到 57.5%，涨了 10 个百分点。
@matt_palmer 用 Grok 4.6 构建《办公室》这款游戏的二维代理模拟时，最直接的感受是速度。吞吐量约为 80 tokens/秒，延迟低，他评价「可以与 Cursor 的 Composer 模式相媲美」。
我们都知道，在需要高频迭代的 Agent 编程场景中，响应速度直接影响工作节奏。
说到价格，Grok 4.6 的 API 价格定在每百万 input token 2 美元、output 6 美元。当 prompt 进入 xAI 的长上下文档（20 万 token 起），价格翻倍到 4 美元/12 美元，且整单所有 token 均按高价计费。
即便如此，短上下文的定价仍比 Claude Opus 5（5 美元/25 美元）和 GPT-5.6 Sol（5 美元/30 美元）低 60% 以上。Artificial Analysis 的数据显示，Grok 4.6 每任务成本约为 0.84 美元，是目前综合能力与单任务成本比最优的模型。
Reddit /r/cursor 版块里有开发者发帖，说自己在日常高负荷开发中用 Grok 4.6 的 High Reasoning 模式做前期架构规划，再把任务下发给轻量级 Agent 完成，感觉「性价比高到有点不真实」。
另有人表示直接从 Claude Opus 4.8 爬墙，原因是「对我的 use case 能完成同样的事，但省了快 70% 的钱」。
高度依赖上下文缓存的 Agent 编程中，调用同等能力的 Claude Opus 每次请求成本约 0.052 美元，DeepSeek V4 Pro 约 0.000875 美元，Grok 4.6 介于两者之间，但在响应速度和综合智能上明显占优。
有测试者分别用 Grok 4.6 和 Claude Opus 5 处理来自马斯克 TERAFAB 大型工厂的三个 3D 场景——黄昏时的外部环境、洁净室生产车间、带有行走工人的中央操作大厅，所有场景均直接通过 API 获取，未做任何编辑。
两个模型都在第一次尝试时成功交付了可运行的代码，但成本差距显著：Grok 4.6 花费 0.38 美元，Claude Opus 5 花费 2.06 美元——同等输出质量下，成本差了 5.4 倍。
此外，Grok 在每个场景中使用的 token 数量也明显更少。
2025 年底，行业共识里的御三家是 OpenAI、Anthropic、Google。
现在看 Artificial Analysis 的总榜前排：Claude Opus 5 (63)、Claude Fable 5 (62)、Grok 4.6 (61)、GPT-5.6 Sol (61)、Kimi K3 (约 59.7)。
Google 不在这张表的前排。
它自 2 月的 Gemini 3.1 Pro 之后就没有发过前沿模型。旗舰 Gemini 3.5 Pro 被报道落后计划数月，至今只在合作伙伴内测；最近一轮 Google 发的是 3.6 Flash、3.5 Flash-Lite 和一个安全垂类的 Flash Cyber。
随着 DeepMind 的 CEO 离任、强化学习团队流失，SemiAnalysis 认为 DeepMind 已经不再是一家前沿实验室。
第三把椅子空出来了一半。
但挤进来的Grok 能坐稳吗？
提到 Grok，我们也不免想到极端言论、对马斯克的过度赞美、图像生成被用来做非自愿的性化内容。对合规和责任 AI 要求严格的企业来说，有些东西不会因为分数变好而消失。
一个月前，Grok Build CLI 在本地初始化和每次任务执行时，以完全隐蔽的形式，在后台将用户的整个本地项目仓库进行强制性打包，并将其传输至 SpaceXAI 的云端服务器上。
所以在 4.6 发布之后，它也面临这样的声音：不会偷偷把我的代码库打包带走吧？
不过，对夹在 Grok 4.6 和 DeepSeek V4 Pro 中间的那些模型来说，今天大概是最难受的一天。
毕竟「不怕朋友过得苦，就怕朋友开路虎。」
