---
title: 清华特奖获得者顾煜贤，加入DeepSeek
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/l7xBcYWYOJqlgUiA0T6D9g
date_published: '2026-07-05'
fetched_at: '2026-07-11T07:35:15+08:00'
source: wewe-rss
---

# 清华特奖获得者顾煜贤，加入DeepSeek

最近，DeepSeek 开启了疯狂招人，岗位涉及算法、研发、产品、运维、数据工程师以及职能等多个部门。
与此同时，DeepSeek V4 正式版将于本月中旬上线。在此前的 DeepSeek V4 论文作者列表中，我们发现了清华大学 2021 级博士生、2025 年研究生特等奖学金获得者顾煜贤（Yuxian Gu）的名字。
就我们所知，顾煜贤已经正式加入了 DeepSeek。
顾煜贤还曾获得 2025 年度苹果博士奖学金以及蚂蚁 In-Tech 奖学金。
「硬件资源受限时，算法创新就成为突破计算瓶颈的关键。」清华人顾煜贤表示。他是清华大学计算机系毕业年级博士生，本科同样毕业于清华大学。
个人主页显示，顾煜贤在清华大学交互式人工智能课题组（Conversational AI, CoAI）学习，师从黄民烈教授。
个人主页地址：https://t1101675.github.io/
他的研究主要关注如何在大语言模型的全生命周期中提升效率，覆盖预训练、下游适配和推理等关键阶段，最近主要从三个方向展开相关研究：
预训练数据筛选：致力于构建理论和算法，优化大语言模型训练中的数据选择过程，从而训练出更强大、更高效的模型。代表性工作包括 PDS、Instruction Pre-training 和 Learning Law。
模型压缩中的知识蒸馏：设计新的方法，将大模型的知识有效迁移到更小、更易部署的模型中。该方向的代表性成果包括 MiniLLM 和 MiniPLM。
高效模型架构：探索并设计新的模型架构，在降低计算成本的同时提升模型性能，相关工作包括 Jet-Nemotron。
在 Google Scholar 主页，顾煜贤的论文引用量已近 5000，超过 1000 的论文有两篇，分别是《Pre-trained models: Past, present and future》和《MiniLLM: Knowledge distillation of large language models》。
顾煜贤作为一作，多次在 NeurIPS、ICLR、ACL 等国际 AI 学术顶会上发表论文。
机器之心在去年报道过「Jet-Nemotron」，一种全新的混合架构语言模型新系列，在达到 SOTA 全注意力模型精度的同时，还具备卓越的效率。
Jet-Nemotron 的核心创新主要体现在以下两点：
后神经架构搜索 (Post Neural Architecture Search，PostNAS)：一种高效的后训练架构探索与自适应 pipeline，可适用于任意预训练的 Transformer 模型。
JetBlock：一种新型的线性注意力模块，其性能显著优于 Mamba2 等先前的设计。
论文地址：https://arxiv.org/pdf/2508.15884
当时，2B 版本的 Jet-Nemotron 性能就能赶超 Qwen3、Qwen2.5、Gemma3 和 Llama3.2 等最 SOTA 开源全注意力语言模型，同时实现了显著的效率提升。在 H100 GPU 上，其生成吞吐量实现了高达 53.6 倍的加速（上下文长度为 256K，最大 batch size）。
在 MMLU 和 MMLU-Pro 基准上，Jet-Nemotron 的准确率也超过了一些 MoE 全注意力模型，如 DeepSeek-V3-Small 和 Moonlight，尽管这些模型的参数规模更大。
在更早的 2024 年，顾煜贤及其合作者提出了一种将大语言模型蒸馏为更小语言模型的知识蒸馏方法，首先利用反向 Kullback-Leibler 散度（KLD）替代标准知识蒸馏方法中的正向 KLD 目标，随后推导出一种有效的优化方法来学习这一目标。
他们将得到的学生模型命名为 「MiniLLM」。在指令跟随场景下的大量实验表明，相比基线方法，MiniLLM 能生成更精准的回答，整体质量更高，同时具有更低的曝光偏差、更好的校准能力，以及更强的长文本生成性能。
谷歌、阿里、英伟达等领先的开源社区和产业平台已采用这一方法。
论文地址：https://arxiv.org/pdf/2306.08543
我们也期待顾煜贤在人生的下一段「DeepSeek」中，带来更多新的成果。
【ICML 2026首尔 · 云帆AI Talent Meetup】最后报名中
7月9日晚，首尔ICML会场旁，上海人工智能实验室、上海科技大学、上海创智学院、阶跃星辰、Sharpa Robotics等20余家上海顶尖AI单位现场设展，开放100+岗位。专场招聘、学术分享、圆桌交流、自由Networking一站式搞定。
扫码即刻报名。
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
