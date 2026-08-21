---
title: DeepSeek的这次小更新，原来藏着两个大招。。。
source_account: 差评X.PIN
source_url: https://mp.weixin.qq.com/s/r3MiF5mlRQpoO2cZWJjpjA
date_published: '2026-08-03'
fetched_at: '2026-08-11T07:33:29+08:00'
source: wewe-rss
---

# DeepSeek的这次小更新，原来藏着两个大招。。。

今天有个 AI 研究员发信息给我说，这是她入行以来最好的夏天。
DeepSeek-V4-Flash 正式版发布了，性能超过此前的 V4-Pro-Preview。
基准测试成绩甚至能和 Claude Fable 5 放在同一张表里比较。
一个总参数 284B、激活参数仅 13B 的 “ 轻量版 ” 模型在多项任务上追平了那个曾经遥不可及的 Opus 4.8。
更离谱的是价格，Flash 版便宜到令人发指，两块就能让它输出 100 万 tokens 她把手头所有的项目都优化了一遍，结果还没花掉一杯奶茶钱。
昨天在开发者群里。 突然所有人停下手里的事，
开始转发评测截图。 她说自己特别开心，
有种人类黄金时代的错觉。
谁也没想到，DeepSeek 这次又给大家憋了个大的，卡着 7 月的尾巴，发布了 DeepSeek V4 Flash 的正式版。
说实话，一开始，世超对这次更新其实是没有太在意的。。。
毕竟只是一个顶着 Flash 名头的模型更新，主力军 Pro 系列更是动都没动。
上一次只更新 Flash ，不更新 Pro 模型的大模型厂商还是谷歌，现在已经成了大家的玩梗对象。
这你一个 Flash 模型再更新，能力总不能超过 Pro 吧。。。
？
？？
不是哥们，你这 Flash 模型怎么比 Pro 模型的跑分都强了？？？
这还是 Flash 吗？
不对 DeepSeek，大模型不是这样玩的，你应该先发一个 Flash 模型，然后说自己只是速度快一些罢了，你怎么直接让 Flash 模型追上了自家的 Pro 模型，然后价格还只卖 2 块钱 / 百万 token，而且时不时还能有个打一折的缓存命中优惠，我周末用了 1 个亿 token 才花掉了 5 块钱。
世超根据这次 V4 Flash 亮出来的跑分整理了一下，可以发现这次 Flash 模型的能力极其夸张。
超过了自己的大哥 Pro 不说，虽然比不上 Claude Opus5、GPT-5.6 Sol、还有 Kimi K3、这些顶级模型。
但是，正式版的 V4 Flash，基本上也就不如这几家了。
有网友把各家大模型的能力和价格，收集到一起做了个表整理了出来：
每个大模型在表上都是一个点，点的位置越靠左边，说明模型越便宜，点的位置越靠上面，说明模型的性能越好。
这样一看就会很直观的发现，市面上绝大多数模型 ，都处在一个很尴尬的位置。
性能没 DeepSeek 好就算了，价格还比 DeepSeek 要贵。
而那些性能比 DeepSeek 要强的模型，处境其实也没好到哪去。
因为它们的价格实在是太贵了。
差友们可能没注意到，上面这张图的横轴，它不是一个线性坐标轴，而是个对数轴。
但咱给模型花钱的时候可不是这么算的。
于是世超稍微动用了一下很久没有用过的 PS 手段，把这张图给拉成了线性坐标轴来看看，发现它的真实比例，其实是这样的。。。
也就是说，论性能的话，Claude Fable 5，GPT-5.6 Sol 这些模型比起 V4 Flash 来说，可能有个这么两成的提升。
但是这些模型的价格，可能也要比 V4 Flash 多了两 0。
夸张一些的话，可以说 DeepSeek 又一次重新定义了模型的斩杀线。
所以，这次 DeepSeek 是怎么做到的？明明模型的架构，参数都没啥变化，为什么一个模型的能力会突然有如此巨大的变化？
世超也是往回翻了翻 DeepSeek 的论文和公开资料，找到了两个概率最大的方向。
首先最重要的一个点就是后训练。
这也是官方承认的，预览版和正式版差距最大的地方了。
这里给对大模型不太了解的差友科普一下，一般来说，我们会把大模型的训练给分成两个阶段。
第一个阶段叫预训练。
在这块，我们需要给模型塞进去海量文本、代码和其他数据，以此来让它学会回答问题的基本能力。
整个过程有点像在培养一个高中生，不管是语数外，还是物化生，政史地，还是音乐美术体育计算机，各种领域的知识都要拿点过来给他，通过这种方式来提高模型的基础能力。
而第二个阶段后训练，则是锻炼的真正干活解题的能力。
这块做的活主要是刷题，让模型通过反反复复地刷题，来提高模型的应试教育能力，让它来学会怎么解决问题。
研究人员会通过监督微调、强化学习和大量任务数据，让模型学会理解指令、拆解问题、使用工具，以及按照人类偏好的方式给出答案。
同样预训练出来的一个模型，在经过了不同的后训练刷题练习之后，是很容易刷出完全不同的表现的。
之前 DeepSeek R1 的论文里就讲过，他们把 V3 拿过来做了 GRPO （ 群组相对策略优化 ） 强化学习之后，模型的数学能力就得到了巨大的提升，在 AIME 2024 测试集上的正确率直接从开始的 15.6% 给飙升到了 71%。
OpenAI 当年的 InstructGPT 也一样。
经过监督微调和 RLHF 之后，一个只有 13 亿参数的模型，在真人盲评里，甚至能打赢参数量大了 100 多倍的 GPT-3。
如果说预训练决定了模型的大脑里有没有相关的知识的话，那么后训练就是决定模型有没有掌握把这些知识给拿出来的能力。
当然，光靠后训练，或许还不能完全解释这次 V4 Flash 的夸张成绩。
仔细看 DeepSeek 的发布说明，大家还能发现一件事：
那就是这次公开的部分跑分，DeepSeek 并不是让模型直接裸跑得出来的。
而是用上了一个叫做 DeepSeek Harness 的未发布工具。
Harness 这个词大家这半年来应该也听过不少，现在热的红火的 Claude Code，Codex，OpenClaw 其实都可以算是 Harness，或者说是 Agent 工具的一种。
就连现在大伙经常刷到的 Workbuddy，Qoder，Trae 也都能算是。
而现在，DeepSeek 要推出自己的 Agent 工具卷进来了。
这件事，可能比单独更新一个模型还要关键得多。
因为在现在这个 Agent 时代，一个模型最后能干出什么成绩，已经不只取决于模型本身有多聪明，还取决于外面给它套了一套什么样的工具。
一个裸模型就像一个坐在考场里的学生，遇到复杂的问题就只能靠自己的脑子硬算。
但 Agent 会给模型安上搜索引擎，能给它配上代码的运行环境，还会帮它管理好项目的上下文，检查项目的运行结果，甚至跑错了还能直接重来一次。
通过这些外置工具给模型上 Buff，AI 实际做事的能力可以得到极大的增强。
今年年初的时候，多伦多大学的团队做了一个研究，他们把同一个大模型，放到不同的 Agent 工具里面来做测试。
结果发现同一个模型，在不同的工具里表现的完全不同，完成问题的概率最高能差个好几倍。
前不久有人说过，现在 AI 的发展，就像一级一级向上爬的阶梯。
去年的阶梯是思维链，通过思维链的方式，我们可以让模型学会自己思考，来让 AI 能做到更多的事情。
而今年，AI 发展最重要的阶梯就是 Agent。
现在，DeepSeek 也交出了自己对 Agent 的答案。
通过高质量的后训练和 Agent 工具，把原本负责轻量应用的 Flash，给直接拉到了全球旗舰模型的身后。
说实话，世超看到这个超级强化后的 Super Pro Max 版本的 Flash 模型，已经开始期待起来了。
既然一个用来打下沉市场的小弟，都能靠着出神入化的后训练和 DeepSeek Harness 工具，跟 GPT-5.6 Sol、Claude Fable 5 这些身娇肉贵的 “ 太上皇 ” 们掰掰手腕……
那要是等 DeepSeek 把这套版本答案，给套在更强的 V4 Pro 上呢？
https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
https://www.reuters.com/business/retail-consumer/deepseeks-new-ai-model-is-by-far-cheapest-well-known-models-run-research-firm-2026-08-03/
https://artificialanalysis.ai/leaderboards/models
https://artificialanalysis.ai/models
https://artificialanalysis.ai/methodology
https://artificialanalysis.ai/methodology/intelligence-benchmarking
https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash
https://arxiv.org/abs/2606.19348
https://api-docs.deepseek.com/zh-cn/news/news260424
https://www.deepseek.com/transparency/
https://arxiv.org/abs/2501.12948
https://arxiv.org/abs/2203.02155
https://arxiv.org/abs/2602.09540
https://swebenchmobile.com/
