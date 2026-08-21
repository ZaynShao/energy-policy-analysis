---
title: DeepSeek的Harness，有一套新世界观｜Hao好聊趋势
source_account: 腾讯科技
source_url: https://mp.weixin.qq.com/s/zm0m1YKbAWvO-b_YdPJGZQ
date_published: '2026-08-15'
fetched_at: '2026-08-17T07:31:22+08:00'
source: wewe-rss
---

# DeepSeek的Harness，有一套新世界观｜Hao好聊趋势

腾讯科技旗下企鹅智库前沿科技论文解读专栏。在代码与商业的交汇处，寻找AI的确定性。
文｜博阳
编辑｜苏扬
8 月 13 日，DeepSeek端上了一道新菜DeepSeekHarness，但这道菜初看让人有点摸不着头脑。
项目首页的介绍是Everything is a Plugin，一切皆插件。
我们其实已经见过太多Harness了，插件在我们理解中似乎就和MCP一样是调用工具的。
但这回，DeepSeek 是把过去 Harness 里很多默认属于Harness「底层框架」的东西也拆成了插件。官方架构文档明确列出的最核心一层有 7 个包，Session（会话日志）、System Prompt（系统提示组装）、Tools（工具系统）、Agent（Agent 注册与接口）、Agent Loop（智能体循环）、Scope（作用域注册）和 LLM（模型适配接口）。
而这在之前的Harness中都是关键的，不更新版本不会动的核心组件。
甚至往外展开以后，默认模型选择、持久化、Sandbox（沙箱）、审批策略、设置、凭据等也全部做成插件。
再上一层，则再加上 Context/Instructions、Compaction（上下文压缩）、Skill、Sub-agent、Workflow、Goal、Jobs、File System、Shell、Storage、UI、API 等。
这里面才是过去Harness里部分开放给插件的部分。
而且除了最底下的 Cordis Runtime（Cordis 运行时）， Agent 几乎没有哪一块天然拥有不可动的特权地位。
而这个不动的 Cordis，只提供六种最基础的操作：装一个组件（use）、记录一次可撤销修改（effect）、提供一种能力（set）、读取一种能力（get）、把同一种能力隔离开（isolate），以及在能力外面加一层使用规则（intercept）。
剩下的事情由 Runtime 自动完成。一个插件缺少依赖，就先不启动，依赖齐了再加载。依赖的组件被替换，它会重新加载。插件退出，它留下的作用会按记录撤销，如果别的插件还依赖它，则先让下游插件退出，再真正把它拿掉。
它管的不是 Agent 怎么干活，而是这些零件怎么装、怎么接、怎么换，以及换完以后怎么安全的把依赖都拆掉。
这确实是一种完全不同于当下市面上所有Harness的模式。不论是CLaude Code还是Codex，乃至Hermes、Pi都是底层核心都给你配置好不能动，想要附加功能可以搭插件的模式。
毫无疑问，市面上的那种Harness更适合开箱即用的C端使用需求和稳定性的要求。而DeepSeek的这套Harness对一般用户来讲，看起来实在太复杂了，光模式就有四种。
实际上，如果你选择标准模式，那基本上就和别的Harness一样，是一套经过DeepSeek 配置好的默认模式。代码模式则是加了程序化工具调用，更适合多工具调用的一种基础配置。
但一般人看到四种模式就已经懵了。为什么要搞这么麻烦呢？
因为DeepSeek做的这套系统，有着更大的一层野心。其出发点也并不是设置好一个最适合开箱即用的Harness架构，而是为了自进化打好基础。
01
DSH不止是个插件系统，而且能让插件真正独立
与 Harness 一同被摆上台面的，还有一篇由北京大学和 DeepSeek-AI Harness负责人崔添翼共同完成的论文《A Programming Paradigm for Spatiotemporal Composability》（时空可组合性的编程范式）。
论文中提出的Harness模式和DSH的构架基本完全一致，可以看作是DSH的理论基础。
从这篇论文中，我们也可以看出DeepSeek的插件和其他插件其实定义上完全不同。它必须是可干净的拆卸，可溯源其影响的插件。
过去的插件系统，像VsCode，拆换插件的解决办法其实就是重启整个进程。整个进程重启以后，cache、连接、partial computation（中间计算状态）等也一起丢掉。为了维持服务，还可能不得不准备副本。
但这只能说明这个系统其实对于某个组件究竟给环境增加了什么，它依赖的是什么也并不清楚，也就无法只撤销这个组件贡献的部分。
但DSH的插件希望做到这一点。
这首先要求 temporal composability（时间可组合性）。独立组件运行后对共享环境造成的修改，在组件卸载时必须能够恢复。
为此作者引入 revertible effects（可回退效应），每一次 effect （模块造成的效应）在执行修改的同时，都向 runtime 返回一个对应的 inverse（逆操作），也就是如何恢复的说明书。runtime 将这些逆操作累积起来，卸载组件时再按相反顺序执行。
论文里有大量的数学推导，它们其实就是在证明，只要每个局部 effect 都能正确给出逆操作，那这些逆操作在堆叠组合以后仍然能正确恢复整个组合。
这时，Harness就可以无损的恢复到没加插件之前的状态，而只撤掉插件自己的贡献。
但如果多个组件同时运行，事情马上变复杂。
假设组件 A 做了一个修改，然后组件 B 又做了另一个修改。现在我想只卸载 A，而保留 B。这意味着 A 的逆操作不再是在「它刚刚执行完」的那个状态上执行，而是在一个已经被 B 改过的状态上执行。
此时要保证，撤销 A，只拿掉 A 的贡献，不能顺手把 B 的东西也毁掉。
所以作者又引入了independence（独立性）。只有互相独立的多个组件，才可以单纯通过这种方法只取消掉它的贡献。
但是现实世界不可能要求所有组件完全独立，组件之间本来就是要互相依赖的。因此就需要Spatial Composability（空间可组合性），去让不同组件之间的依赖被显式表达，而且一个组件出现、消失或者被替换以后，依赖它的组件能自动重新调整自己的状态。
传统的软件系统当然也有 dependency injection（依赖注入），但大多数依赖关系是在初始化阶段解决的。程序启动时把 A 接给 B，之后默认这个关系一直成立。
可在一个真正动态的系统里，这个假设不成立。A 可能运行到一半被卸载，也可能被 A2 替换。此时仅仅知道B 需要 A是不够的，runtime 还必须持续知道A 现在还在不在，B 此刻究竟连接的是谁，以及这种关系发生变化以后 B 应该进入什么状态。
论文把这种能够动态声明、发现和重新协调组件依赖关系的能力称为 spatial composability。
为了解决它，作者引入了第二套机制，叫reactive coeffects（反应式共效应）。如果说 effect 描述的是「这个组件对环境做了什么」，那么 coeffect 描述的就是反过来「这个组件要正常运行，需要环境给它什么。」
比如一个插件可以明确声明，我需要 database 和 logger，另一个插件则声明自己可以提供 database。这样，组件之间原本散落在代码调用中的隐式关系，就被提升成 runtime 可以直接看到的一张依赖的拓扑关系图。
有了这张图，runtime 就可以持续检查一个组件所声明的依赖现在是否全部满足。
如果原本缺少数据库，后来一个新的数据库被装进来了，那么这个组件就从 unsatisfied（依赖未满足）变成 satisfied（依赖满足），runtime 可以自动把它激活。反过来，如果原来依赖的组件消失了，runtime 会让它进入停用流程。
那现在如果要拆卸一个插件，从这一刻开始，新的组件已经不能再把 A 当成可用，依赖 A 的 B 也会发现自己的依赖条件已经不满足，于是开始退出。但 A 原来提供给 B 的 binding（绑定）暂时仍然保留，所以已经依赖 A 的 B 还可以在 teardown（拆卸）过程中继续完成自己的收尾工作。等所有依赖 A 的组件都完成退出之后，A 才真正执行自己的逆操作，把自己对系统的影响彻底撤销。
时间可组合性保证的是「我能把自己留下的东西撤干净」，空间可组合性保证的则是「在我撤掉之前，所有和我发生关系的组件都能被正确处理」。
也正因为效用（effect）和依赖性都被显式化，在DSH中，所有组件/插件的变化才不再是一场对整个程序影响未知的代码替换，而变成了一个影响范围可以被 runtime 追踪和管理的局部操作。
写到这里，我们看到的就是一个很好的插件工程升级，在动态系统中插拔插件变得容易了，很好，那它和自进化又有什么关系呢？
02
Harness自进化的三个两难困境
就在 DeepSeek Harness 发布的前后，AI 研究圈内最火的一个概念就是 Recursive Harness Improvement / Recursive Harness Self-Improvement（RHI，递归式 Harness 自我改进）。
过去几个月，Meta-Harness、AHE、Self-Harness、RHI、HarnessBank、Harness-R1 等论文密集的开始出现。
之所以这个领域火了，是因为它是局部调参这条RSI最成熟路径外，最好操作的一条路径。
一个几百亿、几千亿参数的神经网络，本质上仍然是一个连续、高维、强耦合的参数空间。模型即使知道「自己长期规划做得不好」，也没有一个语义坐标告诉它，第多少层、第多少个参数对应长期规划。真正修改参数，通常还得绕一圈，设计新的数据、奖励、课程或者 RL 环境，再让梯度下降完成更新。
但自进化 Harness 并非如此。 相比直接进化模型权重，它有几个天然的优势。
第一，修改点相对离散。改 Prompt、换 Tool、增加一条 Retry、改变一个 Agent 的通信规则，这些修改本身就是自然语言、代码或者配置。LLM 能看懂，也能直接写。我们需要考虑的优化搜索空间，并不像模型本体那么无穷无尽。
第二，试错便宜。后训练一个模型的成本，比起改改Harness架构可贵太多了。而且容易回退。效果不好，上一版 Harness 还在那里，切回去就行。
其三，则是有快速的现实反馈。当自进化完成一轮修改后，马上就能看到当前 Agent 的行为变化并对其进行评测。
效果确实不错。比如 在2026年 7月Sakana AI发布的《Recursive Harness Self-Improvement》中，研究者在量化金融、机器人和药学三个领域构造了 30 个机器学习研究任务，只用几轮 Harness 更新，就让低 reasoning effort（低推理预算）的 Agent 超过高推理预算模型的表现，同时最多降低约 60% 推理成本。
进一步分析还发现，主要增益并不是模型突然「多想了一会儿」，而是来自任务特定的 Context Management（上下文管理）和更高效的 Agent 间信息流。也就是说，模型没换，工作方式换了，能力就变了。
这让 Harness 看起来像是今天最适合先做 self-improvement（自我改进）的地方。
但根据最近的一系列研究，落地后的RHI可以说是全无统一路径，因为三个问题一直都没有得到澄清。
第一个问题是到底进化什么？
这听起来很奇怪。既然都叫 Harness Improvement，那当然是在优化 Harness。问题是，大家嘴里的 Harness 根本不是同一个东西。
Harness 到底是 Prompt，还是 Prompt + Tool，还是连 Memory、Middleware（中间件）、Agent Topology（智能体拓扑）、Runtime 和 Evaluator（评估器）都算？修改空间的边界在哪里？
3 月，斯坦福发表的《Meta-Harness: End-to-End Optimization of Model Harnesses》（简称Meta-Harness）定义的修改范围其实比较模糊，就是直接把 Harness 的可执行代码交给一个 Coding Agent。这个 Proposer（提案器）可以像程序员查代码仓库一样，自己读取源码、历代候选的成绩和原始执行轨迹，再决定下一版代码怎么改。也就是说，它眼里的 Harness 已经接近「整个决定模型如何保存、检索和看到信息的程序」。
4 月，复旦发表《Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses》（简称 AHE）。这篇文章则直接提出了修改问题混乱的问题，他们认为自动改 Harness 面临的第一个困难，就是heterogeneous action space（异质动作空间），Prompt、工具、Middleware（中间件）、Skill（技能）、长期记忆这些东西性质完全不同，却全混在一个搜索空间里。AHE 的处理方式，是把每一个可编辑组件单独文件化，让修改发生在哪里、改了什么、能不能恢复都更加清楚。它把这叫 component observability（组件可观测性）。
到了 8 月，Luan Zhang 等人的《HarnessCompass: Guiding Automatic Harness Evolution toward Generalizable and Effective Agent Harnesses》（《HarnessCompass：引导 Harness 自动演化走向更好的泛化和效果》）又把问题往前推进了一步。作者发现，如果 Prompt、工具、中间件、记忆等 Harness 组件一起优化，很容易出现 cross-component interference（跨组件干扰）：一个修改覆盖另一个修改，两个修改重复做同一件事，或者彼此抵消。
因此 HarnessCompass 干脆先做 component-wise optimization（组件级优化），分别优化，再重新整合。在 SWE-bench Verified 上，它用 GPT-5.4 只演化 5 轮，就把 Pass@1 从 54% 提升到 66%，同时比此前方法表现出更好的留出任务泛化。
但问题是，改什么，要改的离散部件怎么做处理才比较好，这里面没什么统一的答案。
第二个问题是Harness到底应该怎么进化？
是应该花大成本寻找一个可以跨任务复用的「最好 Harness」，还是承认不同任务、不同模型本来就应该使用不同 Harness，让系统现场适应？
早期大家会想象有一个非常完美的基础 Harness，会适应所有任务。我通过一次次进化，让这个通用Harness变得越来越强大，趋于完美即可。
但最近越来越多证据，对这种玫瑰色想象打了脸。
7 月 14 日，艾伦人工智能研究所发表论文《Rethinking the Evaluation of Harness Evolution for Agents》。它问了一个问题，Harness Evolution（Harness 演化）自己也要花推理预算。为了得到第五版 Harness，你已经看了五轮反馈、跑了五轮任务，那为什么不把同样的计算直接拿去多解几遍题？
于是作者把 Parallel Sampling（并行采样）、Sequential Refinement（连续修订）和 Harness Evolution 放到相同反馈、相同推理预算下比较。结果现有自动 Harness Evolution 并没有稳定胜过简单的测试时扩展方法。
但是我们可以说，至少Harness进化出来的是固定的，搞好了后面省预算啊。
但这个前提是它得确实通用，确实泛化。换一组题它就不好使了，那这么优化有什么意义？
问题就出在这个泛化上了。研究者只在训练任务上演化 Harness，再拿到完全留出的 Terminal-Bench 2.1 任务上测试，Claude Opus 4.6 只比初始 Harness 提升 1.2 个百分点，GPT-5.4 提升为 0，平均只剩 0.6 个百分点。
也就是说，很多看起来很漂亮的 Harness 涨点，很可能吸收了训练任务的特殊反馈，并没有变成真正可以复用的工作原则。
更雪上加霜的是，7 月 20 日UC Berkely的另一篇论文《Automated Discovery Has No Universally Superior Harness》，把这个「泛化不好」的问题做了更深层的推演。研究者们拆开了 OpenEvolve、TTT-Discover 一类自动探索系统，把 Archive（候选档案）、Parent Selection（父代选择）、Exploration（探索策略）、Budget Allocation（预算分配）等部件重新组合成 30 套 Harness，在 12 组「模型—问题」组合上跑了超过 310 万次 LLM Rollout。最后没有任何一套固定 Harness 能在所有模型、所有任务上稳定最好。
作者因此提出，Harness 的选择更像一个依赖具体模型和具体问题的超参数，而不是一张永远正确的万能配方。
也许从一开始，要求「最终 Harness 必须通用」就是错的。但也许，是当前进化的方法不对，要求进化的东西不对？
比如在AHE 论文的实验中，它演化出的 Harness 冻结以后换到其他模型家族，仍然能获得 +5.1 到 +10.1 个百分点的收益，而且真正能够迁移的主要是 Tools（工具）、Middleware（中间件）和 Long-term Memory（长期记忆），而System Prompt（系统提示词）迁移后掉分非常明显。
这意味也许完整的Harness确实不存在通用，但某些 Harness 原语确实可能跨模型、跨任务复用。
8 月的香港城市大学论文《HarnessCompass: Guiding Automatic Harness Evolution toward Generalizable and Effective Agent Harnesses 》，训练Harness Agent的方式是，只拿 SWE-bench Verified 的 50 道题演化 Harness，把另外 450 道完全封存起来，并设置一个 Generalization Gate（泛化门），要求所有修改都必须是特定任务无关的，也就是不能针对某一道具体任务打补丁，而要寻找更普遍的 Harness 改进。
只加这一条约束，留出任务就从 51.6% 提高到 58.4%。
所以现在至少有一条可能的路线，并不是寻找一套万能 Harness，而是主动从大量具体任务里，把那些不依赖具体任务的共同结构筛出来。最终 Harness 可以因任务而异，但 Tool、Memory、Middleware、Recovery、Context Management 这类更小的结构单元，可能逐渐沉淀成一套可以反复调用的通用原语。
但目前，至少有三种完全不同的东西可以叫「通用」。
最强的是一个完整成品通用，所有任务都用同一套 Harness。目前的证据对这个假设越来越不友好。
弱一点的是原语通用，整个 Harness 不一样，但 Tool、Memory、Recovery、Context Management、某些 Agent 协作结构可以跨一批任务复用。
再往上一层，则是适应能力通用。最后长出来的 Harness 完全可以不同，真正稳定的是「看到什么任务、什么模型、什么失败以后，知道应该怎样重新组织 Harness」
第二、第三条路径，哪个更优，似乎也没有最终解。
第三个问题，则是怎么才算真正递归？
如果 Harness 从初始改成版本1，再改成版本2，但负责产生这些修改的 Optimizer（优化器）始终是同一个固定模型、同一套搜索策略，那么不断变化的只是 Harness，怎样改进自己这项能力本身并没有不断进步。
RHI 名字里最重的词其实不是 Harness，而是 Recursive。
今天大部分 RHI 的确都有循环。
当前 Harness 跑任务，得到结果和轨迹。Optimizer 根据这些历史生成下一版 Harness。新 Harness 再跑，再修改。所以版本升级这种进化是确实存在的。
但产生 H1、H2、H3 的那个东西，变了吗？
当下的实践中，大部分时候并没有。
前面的 Meta-Harness、AHE，包括 HarnessBank，本质上都可以让 Harness 一代代变化，但负责提出修改的核心优化器仍然可以是固定的。
优化器读到的历史越来越多，外面的 Archive（档案）、Memory（记忆）、Verifier（验证器）不停在变动，却不意味着怎样修改 Harness 这项能力本身在学习。
在进化的Optimizer（优化器）要到 8 月的论文《Harness-R1: Learning to Edit Executable Runtime Harnesses from Agent Failure Trajectories》中才崭露头角。
在这篇论文中，研究者单独训练了一个 9B Harness Engineer（Harness 工程模型）。它先看目标 Agent 的失败轨迹，生成可执行修改，把修改装回冻结的目标 Agent，再重新运行任务。到这儿为止，它和AHE都很像。
但改动最后真实的性能变化不是只用来决定这个Harness变动补丁要不要留下来，还会直接反过来更新 Harness Engineer。
论文先用 SFT（监督微调）冷启动，再用 Online GRPO（在线组相对策略优化）继续训练。Qwen3.5-9B 的平均成功率从 44.3% 提高到 53.6%。目标 Agent 本身微调以后，专用 Harness Engineer 还能进一步把 59.2% 提高到 64.2%。
这套嵌套元学习的模式，确实非常古老了。但优质的实践，才刚刚开始，远未成熟。
这三个问题都还没解决，都不用上升到我们之前文章提到的如何扩大搜索空间，如何扩大问题域的问题，RHI领域就会一直在一团乱麻之中。
03
一种可能的 Harness 世界观
7 月有一篇MIT CSAIL在研究界挺出圈的文章《Language model harnesses are compositional generalizers》（《语言模型 Harness 是组合泛化器》）。它提供了一种很重要的 Harness 世界观，恰好可以把前面三个看似分散的问题放进同一个框架里理解。
在他们的理解中，Harness 最重要的能力，是承担基础模型不太擅长的更高层的compositional generalization（组合泛化）。
所谓组合泛化，就是碰到一道以前没见过的新题，系统不一定需要重新学习一种完整的新能力，而应该尽可能把自己已经会的东西重新组合起来。
现在的大模型后训练越来越像「哪里不行补哪里」，Coding 不够，就专门做 Coding RL。任务从几十步变成几百步，就继续做更长的 Rollout（执行轨迹）。
这种办法当然有效，但代价是每出现一种新的任务形态，我们都倾向于重新训练模型。但现实世界里的任务组合几乎是无穷的。
今天训练写代码，明天可能就需要查资料写代码。如果每增加一种组合，都要重新把完整任务放进模型训练分布里，泛化就靠一个训练了。
论文的作者认为，这里面缺少的一项能力恰恰是，如果新任务只是旧能力的一种新组合，那干脆找个系统去自己重新组织这些旧能力，这不比重新学一遍省钱吗？
而这个去组合旧能力的系统就是Harness。
Harness 并不是一个单纯包在模型外面的工具箱，它更像外部世界和神经网络之间的一层程序。外面的 Environment State（环境状态）可以很复杂，可能同时包含几百万 Token 的文档、几十个网页、多个 Tool 返回结果、历史状态和 Sub-agent（子 Agent）的中间结果。
基础模型不需要把这一整个世界一次性吞进去，Harness 可以先决定哪些信息留下、哪些信息送进 Context（上下文），任务怎样切分，哪些子任务交给谁，中间结果放在哪里，最后又怎样聚合回来。
好的 Harness 可以先替模型把问题「切好」，把一个整体陌生的大任务拆成很多模型早就会做的小任务。
作者把这种状态叫作 Locally In-Distribution（LID，局部分布内）。整道任务完全可以是 OOD（Out-of-Distribution，分布外）的，但每一次真正送进模型的局部调用，最好仍然落在模型比较熟悉的分布里。
Harness 的意义，就是把第一次见到的完整任务，转换成已经会做的局部动作 + 一种新的组合方式。
虽然这篇论文的目的本身是训练一个会组合原始模型分布内技能的模型RLM，但它提供了一个可能的Harness世界观，去解决我们当下的三个难题。
这个世界观就是：Harness 可以把一个巨大的连续任务世界，重新表示成一个由少数高层动作组成的组合空间。模型不需要记住所有任务，而可以学习怎样组合这些动作。
这恰好给前面 RHI 的第二道困境提供了一个新的出口。在前面的讨论中，我们大概率可以确定没有一套完整 Harness 能够在所有模型和任务组合上稳定最好。
但如果 Harness 本来就是一个组合系统呢？我们并不需要要求所有任务最后使用同一套 Harness。那Harness做的就是在这样一个空间范围内进行组件间的组合泛化。
面对 Coding，可以是一种组合，面对搜索任务可以是另一种，底座模型换了，因为不同模型的弱点不同，组合关系也完全可以跟着改变。
而达成这种泛化需要两个条件。
一是相对稳定的 Harness primitives（Harness 原语）。二是组合这些原语的能力。
如果没有稳定原语，每次面对新任务都重新生成几百行代码，过去的经验很难积累。但如果只有一堆固定组件，没有一套根据当前任务重新组织它们的能力，那又重新退化成了人工设计 Harness。
这样一来，如果未来 Harness 真正承担的是一个高层组合层，那么我们要找的就不再只是「哪些文件允许改」，而是「AI 的工作方式应该被拆成哪些相对稳定的基本动作」。
所以在这种世界观之下，RHI的任务，就变成了逐渐沉淀一套可复用的 Harness 原语，上面则学习一套能够针对 Task（任务）、Model（模型）、Environment（环境）动态组合这些原语的策略。
而这也第一次把前面 RHI 的三道问题一揽子解决了。
进化什么，变成了 Harness 的 Representation（表示）问题：先把一个开放的任意程序空间，逐渐表示成一组稳定、离散、有语义的修改单位。
怎么进化，变成了 Composition（组合）问题：不再追求唯一最优的完整 Harness，而是沉淀可复用原语，并学习不同任务下的组合策略。
如何递归，则变成了 Learning（学习）问题：过去每一次「状态—修改—结果」的经历，能够有效的以此反过来训练负责组合这些原语的优化器。
这套 Harness 的离散元语从哪里来？恰恰就在这里，DeepSeek Harness 的Everything is a Plugin（一切皆插件），就有了RHI方向上的意义。
它做的，正是在把这套元语做出明确的、可学的规范，让 Harness 自己也拥有一套可以被组合，且能够用于自进化的语言。
04
插件，是比原来的功能划分更好的元语
今天让一个 Agent 自己改 Harness，最常用的方式就是给它整个工作仓库，让它去读代码，发现问题，直接 Patch。这种自由度看起来最高，但对 RL来说并不友好。
比如，Meta-Harness 就把整个 Executable Harness Code（可执行 Harness 代码）交给 Coding Agent 修改，自由度最大，但一次修改究竟属于 Prompt、Memory 还是 Workflow，并没有统一的语义坐标。
但强化学习要从过去的经验里学出 Policy（策略），一个最基本的条件是过去和未来的 Action（动作）至少得有某种稳定的共同含义。如果第一个 Action 是修改 Prompt 第 37 行，第二个 Action 是重写一个 500 行 Middleware（中间件），第三个又一次性改变三个 Agent 的通信逻辑，那么虽然这些操作最终都可以用 Token 表达，优化器却很难总结出什么情况下应该重复什么动作。
今天大部分 Harness Evolution 的搜索空间，虽然已经比直接优化模型权重清楚很多，但本质上仍然是代码空间。
我们之前提到，自进化Harness的好处之一就是Harness是离散性的，所以需要尝试调整的部件少。但离散空间完全可能巨大得离谱，比如上面提到Meta Harness用的整个程序空间也是离散的，所有代码最终都可以表示成 Token。
真正要让这些离散的部分有益于后训练，还有一个条件，就是离散信号最好可归因，不耦合，能让 Reward Assignment（奖励归因）这件事变得更干净。
强化学习真正想学的，不只是这次做对了做错了，而是要从最终 Reward 反推出前面哪些选择值得以后继续做，哪些选择应该被削弱。这就是 Credit Assignment（信用分配）的核心作用。
一个任务最后成功了，如果系统只知道整条轨迹成功，却不知道成功主要来自哪一种干预，那么 Reward 就只能粗暴地强化整个行为序列。
真正需要被奖励的，不是一个组件脱离环境之后永恒的价值，而是在当前 Harness 结构下，对某一部分做一次干预所带来的条件收益。
这就是之前那些RHI论文中，把 Harness 切成几个组件的缺陷。
比如 AHE、HarnessCompass ，虽然已经可以把 Prompt、工具、记忆、中间件这些组件拿来分开做实验，但其实这些组件之间仍然可能高度耦合。记忆换掉以后，Workflow 的最佳形态可能跟着变化。而Verifier 单独没有收益，却可能和重复配合以后突然有效。
所以 Reward Assignment 真正困难的地方是这次修改究竟改变了系统里的哪一组关系，最终收益又依赖哪些其他结构。
如果这些耦合关系像之前的RHI论文方案里那样，仍然隐藏在任意代码调用里，那么组件虽然在文件层面被拆开，Reward 依然很难形成稳定、可迁移的训练信号。
DSH 真正可能有价值的地方，就是试图把 Harness 切成有稳定语义、可以独立干预、可以撤销、可以观察影响范围的离散单元。只有这样，最终 Reward 才有机会往这些单元上分。
DSH/Cordis 往前多做的一步，就是它并不假装这些组件彼此独立，而是把「耦合」本身也变成了 Runtime（运行时）可以看到的结构。
一个组件需要声明自己依赖什么能力、由哪个 Provider（能力提供者）提供；Provider 发生变化以后，哪些下游组件因此需要卸载、重新加载，Runtime 都能沿着依赖关系处理。
Cordis 甚至专门讨论了 Mutual Dependencies（相互依赖）。如果两个看似独立的组件实际上存在双向关系，就可以继续拆出专门承载交互的 Integration Component（集成组件）。
也就是说，它追求的不是把复杂系统硬拆成彼此毫无关系的小块，而是把原本藏在程序里的关系，变成显式的节点和连接。
这对 Reward Assignment 的意义很直接。在RSH的框架下，一次 Reward 变化以后，优化器能知道，这次真正替换的是哪个组件，谁依赖这个组件，哪些组件因为这次变化重新加载，新的执行轨迹从哪儿开始起作用。
Spatial Composability（空间可组合性）的意义因此不只是插件之间不会互相搞坏，它实际上给 Reward Attribution（奖励归因）提供了一张结构上的地图，告诉系统这次干预真正波及了哪一个局部子图。
Temporal Composability（时间可组合性）则解决另一个更关键的问题，这些归因能不能通过反事实实验被验证。
Cordis 要求通过 Context 产生的 Effect（效应）携带逆操作，组件卸载时 Runtime 可以恢复这些修改。
于是 Optimizer 可以在当前 Harness 上加入组件 A，跑一次。然后撤销 A，尽量恢复到原状态，再替换成 B，或者测试 A+B。
这时 Reward Assignment 就不再只是看 Log 猜功劳，而开始能够依赖真实 Intervention（干预）去估计在当前结构 H 下，加 A 的边际效果是多少？换成 B 怎么样？
所以从 RL 的角度看，DSH 真正可能比普通 Harness 组件化更优的地方，不是它把搜索空间变得更小，甚至也不只是更离散，而是它把这个空间变得更适合归因。
组件有身份，依赖有结构，运行影响可以追踪，修改还能够局部撤销。这样一次昂贵 Rollout 留下来的就不只是一个最终 Reward，而是「当前结构—这次干预—影响范围—轨迹变化—最终结果」这一整条训练信号。
这件事对 RHI 尤其关键。因为在组合泛化Harness的世界观下， RHI 最终想训练的并不是一台记住无数成功补丁的机器，而是一套越来越会判断「下一次应该改哪里」、「应该在这个情况下如何组合」的优化器。
要做到这一点，Harness 首先必须成为一个可以做 Reward Assignment 的自我修改空间。
从这个意义上说，DSH 的一切皆插件只是第一步。Reward 第一次有机会不是只落到这一版 Harness，而是落到「在这种结构下，这一次结构干预」上。
而只有做到这一层，离散化对于 Harness 自进化的意义才真正成立。
更有意思的是，作为GPRO算法提出者的DeepSeek，这次居然做了一个有利于Reward Assignment 的系统。这是为什么？
GRPO 好用，本身就说明很多时候，一个很粗的终局 Reward 就够了，根本不需要细拆奖励配。
在 Reasoning RL（推理强化学习）里这么粗的信号经常够用，但到了 Agent / Harness RL 里这一套其实就不太好用了。
因为在推理强化学习里，环境中的比较条件相对干净。
同一道数学题，给模型采 16 个回答。16 个 Rollout（执行轨迹）都从同一个题目开始，外部世界在每次Rollout时都没变。一个答案得 1，另一个得 0，我们虽然不知道具体是哪一步造成差异，但至少可以相对有把握地认为Reward 的差异主要来自这 16 条策略轨迹本身。
所以 GRPO 可以选择不追究到底是哪一步有功，而用 Monte Carlo（蒙特卡洛）式的方法干一件比较暴力但有效的事情，让模型把好轨迹整体多学一点。
Rollout 足够多以后，真正反复出现在成功轨迹里的行为自然更容易被强化。
但在 Agentic RL 中，环境也开始进入学习循环，而且环境状态本身会被 Agent 的历史行为改变。
比如一个有长期记忆的 Agent。第一条 Rollout 在第 3 轮写进了一条错误记忆，后面 20 轮都继承这条错误状态。但第二条 Rollout 没写这条记忆。到了第 20 轮，一个成功一个失败。你现在拿最终 Reward 做 GRPO 相对比较，实际上比较的已经不只是两个 Action 哪个更好，而是两个已经分叉很久的环境状态。
这时候事情就不一样了。
今年 5 月的论文《Memory-R2: Fair Credit Assignment for Long-Horizon Memory-Augmented LLM Agents》就拿记忆组件举了个例子。记忆会把 Agent 过去的动作 变成未来 Environment（环境）的一部分。一旦不同 Rollout 写入、修改和删除了不同记忆，它们就不再处于相同的 intermediate state（中间状态）。
论文明确表示，这会破坏 GRPO 这类 group-relative method（组相对方法）进行「公平比较」的条件。因此它专门从相同中间 Memory State 重新 Rollout，比较不同动作的后果。
而7月的TRACE这类 Agentic RL 工作之所以专门做 Turn-level Credit Assignment（轮次级信用分配）或者 Hindsight Credit Assignment（事后信用分配），就是因为终局 Reward 到长时程 Agent 上会越来越稀疏、方差越来越大。
TRACE 甚至直接指出，一条最终失败的 Rollout 里可能包含大量其实正确、有价值的中间 Action，但 Outcome-only RL 会把它们和最后那次错误一起处罚。
因此，Agentic RL，需要一个更稳定的可以进行细化reward Assignment的环境。
而DSH 对 Harness RL 最重要的潜在价值，就是通过可回退效应和显式依赖的插件，提供更稳定的实验状态和更清楚的干预边界，能让用来比较的几次尝试是在足够相似的世界里发生的。
这或许正是 DeepSeek 在 DSH 中藏下的真正底牌。
过去几年，整个行业将绝大部分精力投入在连续参数空间的炼丹中，试图用更大的算力和更多的数据灌出一个全知全能的巨兽。但 DSH 的出现，意味着前沿探索正在向一个新的维度拓荒，从单纯的优化模型权重走向优化智能体工作结构的离散空间。它不再把 Harness 视作供人类调遣 AI 的静态脚手架，而是将其变成了 AI 能够自我感知、自我验证且自我重组的赛博物理法则。
当基础模型的智力增长开始不可避免地遭遇边际效应，这种基于底层原语的组合泛化与自我进化「或许才是通向 AGI 下一阶段的真正钥匙。」
DeepSeek 端出的这道看似繁琐的新菜，从一开始，就不是做给现在的开发者吃的，而是为明天的 AI 准备的进化温床。
推荐阅读
