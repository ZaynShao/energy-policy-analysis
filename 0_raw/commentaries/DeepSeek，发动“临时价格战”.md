---
title: DeepSeek，发动“临时价格战”
source_account: 腾讯科技
source_url: https://mp.weixin.qq.com/s/JSGjqjJSmZ2v1cJvFrAVvA
date_published: '2026-08-13'
fetched_at: '2026-08-14T07:31:40+08:00'
source: wewe-rss
---

# DeepSeek，发动“临时价格战”

DeepSeek创始人梁文锋。图片由AI生成
文｜苏扬
编辑｜徐青阳
8月12日晚，DeepSeek更新官方API文档，旗舰模型DeepSeek V4 Pro 0813正式版（以下统称为V4 Pro）悄然上线。这是继7月31日V4 Flash 0731转正之后，DeepSeekV4这一代产品补上的最后一块拼图。
能力方面，V4 Pro的Agent能力几乎全面提升，知名机构SemiAnalysis表示，DeepSeek V4 Pro和Flash在Agent相关测试中，都甩开了参数更大的英伟达Nemotron 3 Ultra模型。
根据DeepSeek释放的基准测试数据，V4 Pro在终端操作、代码工程等基准测试中“猛追”Opus 4.8、Fable 5这种海外前沿模型，并在部分基准测试中领先。
价格上，V4 Pro定价延续了DeepSeek一贯的“地板价”策略。根据官方页面提供的信息，V4 Pro每百万tokens输入（缓存未命中）3元、输出6元，缓存命中输入低至0.025元。以输出为例，V4 Pro 6元的输出价格仅为Opus 5的三十分之一、Fable5的六十分之一。
不过需要注意，DeepSeek也在官方页面上预告涨价，且涨幅较大。从这个角度来看，平价的V4 Pro可以看作是DeepSeek在新模型上线初期引流的一场“临时价格战”。
01
1M上下文、双API兼容、全功能开放
根据DeepSeek官方文档，V4 Pro正式版模型版本号为DeepSeek V4 Pro 0813，开发者可通过deepseek V4 pro直接调用。与Flash版一致，V4 Pro提供OpenAI格式与Anthropic格式两套接口。
核心规格方面，V4 Pro支持100万tokens上下文窗口与最大38.4万tokens输出，可以一次性读入大型代码仓库、企业知识库或长篇文档，并支撑长时间、多步骤的Agent任务。
模型默认开启思考模式，同时支持切换为非思考模式，开发者可在响应速度与推理深度之间自主选择。
V4 Pro与Flash版完全一致：Json Output、Tool Calls、Responses API、Anthropic API、对话前缀续写（Beta）全部支持；FIM补全（Beta）则在非思考模式下可用。这意味着DeepSeek在接口层面已经完整对齐了当前主流的Agent开发工具链。
价格方面，V4 Pro每百万tokens输入（缓存未命中）3元、输出6元，缓存命中输入低至0.025元；Flash版对应价格为1元、2元与0.02元，两者价差恰好三倍，形成“高频轻量任务走Flash、复杂推理任务走Pro”的清晰产品分层。
另外，在并发限制方面，Pro为500，Flash为2500，进一步印证了两者的定位差异。
02
Agent能力代际跃升
根据DeepSeek官方释放的信息，V4 Pro 0813在终端操作、代码工程、工具调用、安全攻防等维度的基准测试中“猛追”Fable 5这种海外前沿模型，并在部分基准测试中领先。
其中，考察模型在真实终端环境中执行命令、解决系统问题的能力的Terminal Bench 2.1中得分87.9；面向AI安全攻防场景的Cybergym中得分83.3；聚焦软件工程与数据科学全栈任务的DeepSWE与DSBench中分别为62.7、71.1（DSBench-FullStack）、67.2（DSBench-Hard）；在考察知识推理深度的HLE（Humanity’s Last Exam）上，无工具/带工具成绩分别为42.7/60.0；在衡量自动化流程的完成质量的AutomationBench中得分31.8。
相比4月发布的V4-Pro预览版，正式版基准测试释放的能力数据，可以说是代际级别的提升：DeepSWE从12.8跃升至62.7，提升近5倍；Cybergym从52.7升至83.3；AutomationBench从12.8升至31.8；DSBench-Hard从31.1翻倍至67.2；Terminal Bench 2.1也从72.1提升至87.9。
Agent能力的全面暴涨，是本次正式版最核心的升级信号。
与V4-Flash-0731（平均分约57.4）相比，V4 Pro在全部九项基准评测中保持领先，尤其在DeepSWE（62.7对54.4）、DSBench-Hard（67.2对59.6）等高难度任务上拉开了明显差距。
不过也要注意，在主流基准测试中，V4 Pro并非全面碾压：在HLE无工具（纯知识推理）与NL2Repo（代码库理解）两个维度上，它与Anthropic旗舰仍存在实打实的差距。比较有意思的是——HLE加入工具调用后，V4 Pro以60.0对57.9反超Opus 4.8，显示其工具使用能力已能弥补纯推理的短板。
03
“打爆英伟达”不靠参数
V4 Pro正式版上线后，海外分析机构迅速给出反应。
知名半导体与AI分析机构SemiAnalysis在X平台发文祝贺DeepSeek发布V4 Pro 0813（推文中称其为“1.5T”模型），并直言其在Agent任务上“大幅击败NVIDIA的Nemotron 3 Ultra”（massively beats Nemotron3 Ultra on agentic tasks）。
SemiAnalysis同时指出，定位更低的V4-Flash 0731同样大幅领先Nemotron 3 Ultra——而Flash的激活参数比后者少4.2倍、总参数少近2倍。
其引用的Terminal Bench 2.1数据显示：Nemotron 3 Ultra（NVFP4）得分53.9，相比“轻量版”的Flash，也差了29分，Pro的领先幅度更达到34分。
除了吹捧DeepSeek外，SemiAnalysis还在跟帖中附上了对Nemotron模式的批评——Nemotron联盟由多个实验室和公司组成，由NVIDIA与Mistral AI共同主导一个基础模型训练，该模型将开源，并作为后续Nemotron 4系列模型的基础。SemiAnalysis认为这种联盟松散不利于和DeepSeek这样的实验室竞争，应该在联盟内部采用“赛马机制”引导创新。
Semianalysis贴出来的有关V4 Pro和Flash模型在“Agent”能力上超越英伟达Nemotron 3 Ultra的数据，主要反映在两个方面：一个是广度，一个是能力进化幅度。
关于覆盖的广度，前面提到过。V4 Pro的Agent能力并非依赖单点突破，而是横跨九个维度全面铺开：终端操作、软件工程、数据科学全栈、安全攻防等九个维度，都在追前沿模型，甚至超过，这种全链条的能力支持，恰恰是Agent模型的核心竞争力。
很简单，当前的Agent任务，都需要长时间、多步骤地调用工具、处理异常、串联任务，任何一块短板都会导致整条任务链断裂，所以对模型的要求不是某一项激进的领先，而是要在各个维度对能力均衡的拔高。
所以在提升的幅度上，与4月的Preview版相比，V4 Pro正式版在Agent维度完成了近乎重做的升级：DeepSWE提升近5倍、Cybergym提升58%、AutomationBench提升约1.5倍、DSBench-Hard翻倍等等。
另外，Flash 0731在Terminal Bench 2.1上同样拿到82.7分，也超过英伟达的Nemotron 3 Ultra，说明整个V4系列的Agent能力底座已经整体抬升。
结合SemiAnalysis提到的参数效率（激活参数少4.2倍），DeepSeek实际上还证明了一件事：Agent能力的领先，可以不再依赖参数规模的堆砌。
还有一个值得注意的信号：DeepSeek的Agent团队组建。
据公开报道，该团队于今年5月在DeepSeek内部立项组建，由崔添翼（浙江大学计算机学院毕业、曾任职Jane Street近九年）担任负责人，首批开放研究员、研发工程师、产品经理三类岗位；崔添翼在社交平台公开表示“部门仍然非常缺人，每天都在面试”，并于8月2日面向全球开发者征集Harness内测用户。
8月11日前后，“DeepSeek Harness团队”微信公众号完成注册，认证主体为北京深度求索人工智能基础技术研究有限公司，尚未发布内容——这被外界普遍解读为Harness产品即将发布的前兆。
04
价格战与“临时性价比”
与前沿模型基准测试对比中，可以清楚看到：对阵Claude Opus 4.8，V4Pro基本打平。
在双方均有数据的评测项中，V4Pro赢下五项：Terminal Bench 2.1（87.9对85.0）、Cybergym（83.3对78.3）、DeepSWE（62.7对58.0）、AutomationBench（31.8对27.2）以及HLE带工具（60.0对57.9）；Agents’Last Exam双方战平（25.7对25.7）；在HLE无工具（42.7对49.8）、NL2Repo（61.5对69.7）等项目中落后。
从均值的角度来看，V4 Pro为62.8，Opus 4.8为62.6——几乎完全持平。
对阵Claude Fable 5，V4Pro贴身紧逼。V4 Pro在Cybergym上以83.3对83.1实现反超，AutomationBench以31.8对29.1胜出，Terminal Bench 2.1仅差0.1分（87.9对88.0）。平均分62.8对70.5，V4Pro达到Anthropic最新旗舰约九成的水平。
Terminal Bench 2.1一项的对比尤其直观：Fable5得分88.0、输出价50美元，V4Pro得分87.9、输出价0.87美元——分数相差0.1，价格相差57倍。也就是说，同样跻身第一梯队的终端Agent能力，两者的“入场券”成本完全不在一个量级。
如果纵向对比，V4-Pro-Preview与正式版定价完全相同，Terminal Bench成绩却从72.1跃升至87.9，这也可以变相看成加量不加价。
Agent能力大幅度跃升，但业界对DeepSeek的共识在于——价格杀伤力。
根据公开资料，Anthropic高端旗舰Claude Opus 5每百万tokens输入5美元、输出25美元（约合人民币36元/180元，与Opus 4.8定价相同）；最新旗舰Fable 5输入10美元、输出50美元（约72元/360元）。
以此计算，V4 Pro 6元的输出价格仅为Opus5的三十分之一、Fable5的六十分之一。
在整个前沿模型市场，DeepSeek的价格优势仍然明显：OpenAI旗舰GPT-5.6 Sol输出30美元（约216元）、均衡型的GPT-5.6 Terra输出12美元（约86元）；定位Coding/Agent主力的Claude Sonnet 5输出10美元（约72元）。
可以说，DeepSeek用V4 Pro把旗舰级Agent模型的价格基准线，直接拉低了一个数量级。不过，这一价格窗口可能不会持续太久。DeepSeek已在官方页面明确标注：“计划近期整体上调DeepSeekAPI服务的定价，预计涨幅较大。”
所以，DeepSeek V4 Pro正式版“三十分之一、六十分之一”价差，本质上是发布初期的窗口期定价——对于正在选型Agent底座的开发者而言，当前的低价既是红利，也是倒计时。
但要知道，相比海外模型，DeepSeek即便是涨价，在能力项毕竟前沿模型的同时，依旧有非常高的价格调控空间，或者说性价比优势。而关于涨价，Kimi企业业务负责人黄震昕的此前的观点值得思考。他说：“开源模型、中国大模型不该被贴上低价标签，我们做出了SOTA级模型,也能匹配合理商业定价。”
推荐阅读
