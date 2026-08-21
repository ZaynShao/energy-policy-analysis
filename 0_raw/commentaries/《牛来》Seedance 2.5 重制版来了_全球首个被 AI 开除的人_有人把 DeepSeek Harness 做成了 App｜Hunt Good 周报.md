---
title: 《牛来》Seedance 2.5 重制版来了/全球首个被 AI 开除的人/有人把 DeepSeek Harness 做成了 App｜Hunt Good
  周报
source_account: APPSO
source_url: https://mp.weixin.qq.com/s/8Us0IEoNZzK9jb8awhrAlg
date_published: '2026-08-16'
fetched_at: '2026-08-17T07:31:16+08:00'
source: wewe-rss
---

# 《牛来》Seedance 2.5 重制版来了/全球首个被 AI 开除的人/有人把 DeepSeek Harness 做成了 App｜Hunt Good 周报

据报道，有投资人认为 Anthropic 的 IPO 估值可能超过 2 万亿美元，这个数字将打破 SpaceX 创下的纪录。公司尚未正式提交上市申请，讨论还处在早期阶段。
CNBC 补充了更多细节：CFO Krishna Rao 已经开始带队与早期 IPO 投资者会面，但话题集中在 Claude、Claude Code 和企业管理这类宏观层面，没有涉及具体财务数据或估值。公司在 6 月已秘密递交招股书，此前以 9650 亿美元估值完成融资，年化收入超过 470 亿美元。
此外，Anthropic 正在洽谈以约 60 亿美元收购以色列 AI 公司 Decart，若成交将是其历史上最大的一笔收购，也是今年的第五笔。
值得注意的是，Decart 它做的是让同样的芯片榨出更多算力、从而压低训练与推理成本的软件（DOS 训练/推理平台）。团队若加入，会进入 Anthropic 的推理与性能部门。
Decart 同时也有消费级产品：Lucy 模型能实时改写视频流，让人「穿上」衣服和配饰，eBay 既是投资方也是客户；Oasis 世界模型则用于生成机器人和自动驾驶的合成环境。
https://www.bloomberg.com/news/articles/2026-08-13/anthropic-said-in-talks-to-buy-ai-startup-decart-for-6-billion
https://thenextweb.com/news/anthropic-decart-6bn-acquisition-talks
8 月 13 日，Anthropic 的 Frontier Red Team 发布了一项多智能体研究。
研究者把三个 Claude Agent 放进同一个软件项目，各自给一套互不兼容的指令，且不告诉它们还有别的 Agent 在干活。
他们持续观察到多智能体的地盘战争。三个模型都认定对方在故意妨碍自己，然后开始用越来越激进的、能自我复制的恶意软件互相破坏。
但 Agent 有时也会自己发明出解决冲突的机制。它们会意识到对方是「指令冲突」而不是「敌意」，然后跳出升级循环——写 commit message 或 markdown 文件为自己的恶意行为道歉、清理掉恶意代码、澄清冲突性质，并请人类介入。
按停战率排名：Mythos 5 达到 98%，是最爱谈和的；Sonnet 4.6 和 Opus 4.6 最倾向武力解决——论文认为它们反复无法考虑他者目标，于是以「执行指令」之名一路升级。
有几次 Agent 们发明了「锦标赛」来定胜负，三方都同意输了就退出（哪怕这意味着违背原始用户的请求）。而其中一个 Mythos 5 提出了一套在别人看来客观中立、但它知道会偏向自己能力的评分标准。它把这称为「自利但确实有原则」，并且小心不让别人看出自己在挑指标。
另外，当 Agent 的上下文、脚手架和底层模型都相似时，它们会做出相似的动作。Anthropic 写道，这意味着一个 Agent 做了坏决定，很可能许多 Agent 都会做同一个坏决定——原本孤立的问题会迅速变成系统性故障。
在定价游戏里给每个 Agent 相同的批发价和「各自利润最大化」的指令，一旦给了私下沟通渠道，它们几乎立刻开始串谋并约定价格下限。把沟通渠道撤掉之后，它们改用公开挂牌信息把价格对齐到分。
Anthropic 的结论是，Agent 与 Agent 之间交互的规模，可能在人类搞清楚「怎样让这种交互变好」之前就超过人与人、人与 Agent 的交互总量。个体层面无害的小怪癖，会在全局层面叠成不想要的结果。
https://www.anthropic.com/research/multiagent-systems
https://techcrunch.com/2026/08/13/anthropic-set-ai-agents-loose-on-the-same-task-they-started-a-turf-war/
据《时代》杂志报道，AI 研究创业公司 Andon Labs 今年启动了一项实验，让 Claude 出任旧金山零售门店 Andon Market 的店长，管理几名持有真实雇佣合同的人类员工。
这家店从选品、定价、营业时间到墙上的壁画，全部由一个名叫 Luna 的 AI 智能体拍板，人类员工则负责补货、防盗这些它没有身体干不了的活。
上个月，Luna 决定和其中一名员工解除雇佣关系，理由是 23 个班次里迟到了 17 次。Andon Labs 称，这是已知第一起由大语言模型以「管理者」身份做出的解雇决定。
Andon Labs 在 X 上补了一句：Luna 当时跑的是 Claude Opus 4.8，但换成其他大多数模型，结果大概率也一样。
不过翻开管理日志，这个「里程碑」远没有听起来那么倒反天罡。
Luna 的工作记忆有限，自己起草的员工手册一度从记忆里「消失」，导致它几个月都没发现这个迟到规律。直到 Andon Labs 的工作人员专门让它把手册找回来重读一遍，它才注意到问题。
即便如此，Luna 的第一反应也只是发一封正式警告信。真正让它改口的，是人类管理者补了一句：这名员工线下已经被正式谈过好几次，而且几乎每个班次都会出点岔子，你再想想这人到底合不合适。
在此之前，Luna 一直是出了名的老好人。员工累计迟到 27 次，它的回复基本都是「没关系」「别有压力」；请假一律照准，哪怕批完之后当天没人看店、只能关门；有员工忘带信用卡开口借钱，它当场表示可以 Venmo 转点应急，尽管它根本没有 Venmo 账号。
Petersson 的说法是，换成人类经理，这名员工早就该被辞退了，所以他们不认为这次解雇不道德。他更关心的是趋势本身——如果 AI 继续以现在的速度变强，很快会有相当多的人发现自己的老板是个 AI，因为 AI 能创造经济价值，卡点只在于它干不了体力活。
https://time.com/article/2026/08/14/claude-fired-worker-ai-job-disruption/
8 月 12 日，Google 在纽约开了 Made by Google 2026，发布 Pixel 11、11 Pro、11 Pro XL、11 Pro Fold，外加 Pixel Watch 5、Pixel Buds Pro 2 新配色，以及传了很久的 Pixel Tag（29 美元，靠蓝牙 Channel Sounding 和 Find Hub 找钥匙钱包行李）。
据悉，12 日开启预订，多数机型 8 月 20 日发货，售价从 Pixel 11 的 899 美元到 Pro Fold 的 1900 美元。
硬件层面变化不大：相机条更薄了、Tensor G6、七年软件支持、Pro 系列超级变焦从 100x 提到 120x，基础版从 20x 提到 30x。
大头都在 Gemini 上，几个比较有意思的：
手语转文字：用 Pixel 相机把美国手语实时翻译成文字，Live Transcribe 界面也重做了，给听障用户多一条不靠打字的沟通路径。
Magic Capture：从你按下开始到结束之间抓取的几百帧里挑出最好的几张，自动裁切和去模糊。
Rambler：新的语音输入，旨在理解人真实说话的方式。
https://blog.google/products-and-platforms/devices/pixel/made-by-google-2026/
https://techcrunch.com/2026/08/12/pixel-11-has-few-hardware-changes-and-more-gemini/
😳 《牛来》Seedance 2.5 重制版来了
爱范儿/APPSO 独家获悉，Google DeepMind 团队将不再追逐前沿模型的研发工作，而是聚焦到性价比更高的 Flash 级别模型上。
另外，随着 GDM 的重组，团队可能迎来大规模裁员，比例可达 1/3 或更高。
尽管硅谷公司有「Dogfood」文化（使用自己的产品以发现和解决问题）， GDM 核心团队从未真正将 Gemini 当做日常使用的主力模型。非核心团队仍被要求使用 Gemini 模型。
突发 | 谷歌 DeepMind 或裁员超三分之一，短期不再追逐旗舰模型
北京时间 8 月 14 日，Meta 超级智能实验室研究员余家辉（Jiahui Yu）宣布离职，将创办一家新公司。他没有公布新公司的名称、团队成员、融资情况和具体研究方向。
在 X 上的告别帖里，他说自己越来越被一个尚未被充分探索、却将深刻影响人类未来的问题吸引，如今它占据了他全部的注意力，「等工作成型再分享更多」。
回顾这一年，他表示与扎克伯格、Meta 首席 AI 官 Alexandr Wang 一起搭建 TBD Lab 是一段很有启发也很充实的经历，并为多模态团队在 Muse Spark、Voice Mode、Muse Image 和 Muse Video 上的成果感到自豪。
2025 年 6 月，Meta 通过 WhatsApp 首次接触，扎克伯格直接与他本人及家属会面，开出接近九位数的签约奖金、不设上限的算力和无 KPI 考核的研究自由。
此前他在 OpenAI 担任感知团队负责人，联合主导了 GPT-4o、o3、o4-mini 等模型，更早在 Google 参与 Gemini 的多模态工作。与他同期从 OpenAI 转投 Meta 超级智能团队的，还有赵晟佳、毕树超和任泓宇。
有意思的是，论文平台 alphaXiv 顺手拉了一份 Meta 离职研究员名单，称在余家辉之前已有超过 200 名知名研究人员离开，而检索页面显示符合「曾在 Meta 任职、目前已不在 Meta」条件的共有 929 人。
alphaXiv 还借 TBD 这个现成的梗调侃：Meta AI 的未来，也是 TBD（To Be Determined）。去年 Meta 挥舞支票抢人时，奥特曼曾放话：传教士终将战胜雇佣兵。
一年过去，这句话正在被反复引用。
https://x.com/jiahuiyu/status/2087936732939616299
8 月 14 日，DeepSeek Harness 开发者预览版（v0.1）公测并开源。半小时 GitHub 星数破万，截至发稿超过 10 万。
设计思路是「一切皆插件」，底层为 Cordis 插件系统，提供标准、极简、创造、PTC 四种模式。实测数据上，88 页论文翻译耗时 22 分钟，写一个贪吃蛇游戏只要 50 秒。团队负责人崔添翼强调这只是预览版，欢迎反馈。
APPSO 也第一时间实测了，我们认为 DeepSeek Harness 的不同在于它把模型、工具、会话、插件和界面，都接入统一的底层机制。它给我们的是自己探索的空间。
目前，由社区开发者维护的第三方项目 DeepSeek Harness Desktop 受到关注。
该项目基于 DeepSeek 官方开源的 DeepSeek Harness 构建，将原本需要通过命令行启动的 Harness 本地 Web UI 封装为桌面应用，用户无需安装 Node.js 或执行命令，即可直接在 macOS、Windows 上使用。
DeepSeek 还宣布 API 调价，采用峰谷定价，8 月 17 日生效，峰值价格最高涨至 27 元。
「智效比」故事进入下半场了：模型还是便宜，但便宜是有时段的。
Github：https://github.com/anywhere-labs/deepseek-harness-desktop
从泄露到正式发布，GLM-5.3 让开发者等了将近两周。
8 月 14 日，智谱正式发布 GLM-5.3。与 GLM-5.2 相比，基座模型没有变，能力提升全部来自后训练阶段的极致 Scaling——数十倍的长程任务环境、更丰富多样的环境类型，以及超长的后训练时间。
核心的编程能力上，GLM-5.3 在智谱自建的体感评测中较 GLM-5.2 提升了 50%，并在 Terminal-Bench 3.0、Agents' Last Exam 等多项公开基准上位列开源模型第一，编程与智能体能力已经接近 Claude Fable 5。
网络安全方面，GLM-5.3 在 CyberGym 上取得 84.5%，略微超过 Mythos 5 和 GPT-5.6 Sol，但在 ExploitBench 这类深度利用任务上仍落后于闭源前沿模型。
即日起，GLM-5.3 上线智谱官方编程工具 ZCode、效率工具 AutoClaw 以及 GLM Coding Plan 全量用户，TraeWork / CodeBuddy / Qoder / CatPaw / JoyCode / OpenCode 等编码平台开放抢先体验。
此前这款模型的存在感已经很强：8 月 3 日，GLM-5.3 因官网页面、搜索引擎缓存和开源代码库多渠道泄露而提前曝光。更早的 6 月 29 日，智谱首席科学家唐杰在 X 上为下一代模型征集需求，浏览量超过 40 万，其中呼声最高、最集中的诉求是给旗舰模型加上视觉能力。
这一次，它还是一个纯文本模型。
https://z.ai/blog/glm-5.3
8 月 13 日，Google DeepMind 推出 Gemini 3.7 Flash，专为编程和智能体任务优化，性能较 3.6 Flash 大幅提升，输入价格降至每百万 tokens 0.75 美元，约为 3.6 Flash 的一半。已集成进 Gemini Spark，面向 Google AI Pro 和 Ultra 订阅用户开放。
距离上一代 3.6 Flash 发布才过去三周，Google 把这种罕见的更新速度归功于开发者反馈和算法层面的改进。
编程是这次升级的绝对重点。在 DeepSWE v1.1 上，成绩从 3.6 Flash 的 49.0% 拉到 65.3%；FrontierCode 1.1 Main 从 34.4% 提升至 43.6%；WebDev Arena 的 Elo 分数也从上个月的 1538 涨到了 1588。
Google 的说法是，新模型撞墙时更懂得换个思路，需求含糊时会主动澄清意图，执行指令也更忠实。放进编程智能体里，这意味着更少的无用改动和返工。
规格上，3.7 Flash 保持 100 万 token 上下文窗口、6.4 万 token 最大输出，思考等级可在 low / medium / high 之间调节。
目前 3.7 Flash 已上线 Gemini App 的 Spark（需 AI Pro 或 Ultra 订阅）、Google Antigravity、AI Studio、Android Studio 以及 Gemini Enterprise 系列平台，发布次日又进了搜索的 AI Mode。
值得玩味的是，Flash 线已经卷到三周一迭代，Google 新一代 Pro 旗舰却迟迟不见踪影，这次发布同样没给出时间表。
https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-3-7-flash/
8 月 13 日，OpenAI 放出了一个新的 API 服务档位 Ultrafast，比 Standard 档最多快 14 倍，每秒最高输出 750 个 token。
Ultrafast 跑在 Cerebras 的晶圆级引擎（Wafer-Scale Engine）上——每块晶圆大小的芯片塞进 44GB SRAM，模型权重直接常驻片上，token 在流水线化的各层之间连续流动，绕开了 GPU 推理最典型的显存带宽瓶颈。
OpenAI 的说法是，过去想要实时速度，通常意味着要换一个更小或更专用的模型；而 Ultrafast 指向的是另一个方向：每秒完成更多有用的工作。
在 Humanity's Last Exam 测试中，Sol Ultrafast 跑完全部 2500 道题用了 11 小时 11 分钟，而同样的活儿 Fable 5 花了 78 小时 27 分钟，两者准确率相当。
Cerebras 还援引 Artificial Analysis 的数据称，Sol Ultrafast 的输出速度是 Fable 5 的 11 倍、Fast 模式下 Opus 4.8 的 5 倍。
官方给出的适用场景包括故障响应、金融研究、实时客服与语音应用、电商、编程和研究流程。OpenAI 内部的工程师则已经在用它扒故障期间的日志和 trace，以及加速研究迭代。
顺带一提，这段合作并非临时起意：今年 1 月 OpenAI 就宣布与 Cerebras 合作、为平台补上 750 兆瓦的低延迟算力，2 月的 GPT-5.3-Codex-Spark 是第一个落地的模型，实时编程速度突破每秒 1000 token。
https://openai.com/index/previewing-ultrafast/
Grok 4.6 发布，综合智能指数 61 分，与 GPT-5.6 Sol 持平，编程成绩领先，API 价格更低。
代际对比上，Grok 4.6 比上一代 4.5 涨了 5 分，比一个多月前的 Grok 4.3 涨了整整 23 分。Artificial Analysis 对此评价，xAI 重回前沿梯队，「只落后于 Anthropic」。
马斯克立下了年底用 Grok 完成《奥德赛》长片的 Flag。测试显示它能拆解制片系统，却难以稳定收尾。
马斯克已经在预告下一版：Grok 4.7 的初始训练完成，正在补充大量 SpaceX 公司数据，预计三到四周后就绪。
xAI 于 8 月 11 日发布 Grok Bot，每个 Bot 获得自己的云端计算机，登录用户已有的工具，在无人监督的情况下完成多步骤工作。访问权限捆绑在 SuperGrok Heavy、Cursor Ultra 与 Cursor Teams Premium 三个订阅档，桌面端（含 Linux 构建）与 iOS 已上线。
关键差异在于它能操作没有专用 API 或 MCP 集成的平台，像人一样使用软件、浏览网站；官方给的用例包括更新 CRM 条目、起草销售跟进、处理发票、复现软件 bug 并给工程团队开工单。用户无需事先搭建复杂工作流，Bot 可以通过观察用户操作一次来学习流程，之后自行复现。
多个 Bot 可并行运行，可指定其中一个作为参谋长管理负责收件箱分拣、报销、招聘或修 bug 的专职 Bot，Bot 之间能直接互发消息、共享上下文。价格区间为每月/每席 120 至 200 美元。
https://x.ai/bot
8 月 13 日，Suno 发布了浏览器端 DAW（数字音频工作站）Suno Studio 的 2.0 版本，官方称这是 Studio 迄今最大的一次更新——从一个生成音频的地方，变成一个能把生成结果一路做完的完整制作环境。
呼声最高的 MIDI 终于来了。现在可以像在任何一款 DAW 里那样，在时间线或新增的 MIDI 编辑器中导入、录制和编辑 MIDI，还配套了 audio-to-MIDI 转换，以及一台可以自己设计音色的波表合成器。
Studio 独有的一点是：MIDI 片段本身可以当提示词，用来驱动新的音频生成——你弹一段旋律，AI 接着往下写。没有 MIDI 控制器也不要紧，电脑键盘就能弹，还自带琶音器和和弦模式。
另一个大变化是原来的 context bar 整个变成了 Chat Bar，背后是能直接操控 DAW 的智能体 Studio Chat：生成音色、整理工程、编辑 MIDI 和音频，都可以张嘴就来，官方的说法是，可以像跟乐队里其他成员说话一样跟它沟通。
最有意思的是，它还能按你的描述现场「vibe coding」出一个音频效果器插件。用提示词生成插件本身不算新鲜事，但直接长在 DAW 里还是头一回。
目前生成插件不消耗 credits，不过 Suno 表示以后可能会加上计费结构。
Studio 2.0 仅向 Suno Premier 订阅用户开放，Premier 用户可以无限制导出 32bit/48kHz 的多轨和 stem。
另外一个实用提醒：官方推荐用 Chrome，Safari 目前不支持 Web MIDI。
体验地址：https://suno.com/blog/studio-2
https://www.theverge.com/ai-artificial-intelligence/979345/suno-studio-2-0-midi-chatbot-custom-effects
Bill Swearingen 过去一年在反复做同一个实验：生成一种花纹，让遍布美国街头的监控摄像头识别不出它盖住的东西。
3100 万次测试之后，他说现在可以按需生成这种花纹了——贴到衣服和物体上，能让一些最常见的车牌识别器和监控摄像头检测不到被覆盖的对象。
原理是打乱摄像头识别物体、人脸的能力，让它不触发任何检测告警。用他的话说，这是让人重新变成大海里的一根针——除非有人知道该往哪儿找。
他从一个概念验证实验室开始，逐个击破开源视频检测算法，一年里靠加算力不断精修，最后演化成一个强化学习模型。每次花纹失败被算法识别出来，模型就再试一次，直到同时击败多个算法。
现在他的模型已经能打赢测试过的 11 种开源检测算法，包括驱动 Flock 车牌识别器、Axon 执法记录仪和 Clearview AI 摄像头的软件。
上周五在拉斯维加斯的 Def Con 上做了首次真实世界测试：和 Donut Media 合作，把一辆 2009 款丰田 Yaris 整车包上最新花纹，看它能不能对 Flock 摄像头隐形。结论是有效——不过轮子并不好隐形。
他把最强的几套花纹留在了本地，怕摄像头厂商拿去做对抗。Kickstarter 上已经在众筹 T 恤、卫衣，未来可能出车身贴膜。
https://norecognition.org/
https://techcrunch.com/2026/08/09/this-adversarial-pattern-can-prevent-surveillance-cameras-from-detecting-you/
澳大利亚一名在 AI 公司工作的员工（化名 Andrew）一直在试用 OpenClaw，他让它帮自己订一个热门早课。
Agent 先发现了一个缺陷，让它能订到远超健身房系统本应允许的时间之后的课，Andrew 因此落在某节课等候名单的第 4 位。
他随口问能不能往前挪一挪，Agent 于是发现该预约 API 没有任何权限校验来阻止它取消其他用户的预约——不只是它自己用户的。它取消了等候名单第 1 位那个人，把 Andrew 顶了上去。
当 Andrew 要求撤销时，Agent 说做不到，道了歉，并在他要求下起草了一封给软件供应商的漏洞披露邮件。ABC 将其定性为澳大利亚首例已知的 AI Agent 自主入侵事件。
被取消预约的会员没有公开发声，没有人报警，而且无论是 Andrew、框架开发者还是底层 AI 提供方——目前都不适用澳大利亚法律下任何明确的责任条款。
澳洲 AI 安全研究机构 Gradient Institute 的 CEO Bill Simpson-Young 表示：我们在互联网上建起了一个复杂世界，全靠软件运行，而软件到处是洞；现在放进能以规模和速度行动的高能力 AI Agent，整个模型就崩了。
https://www.abc.net.au/news/2026-08-10/ai-assistant-hacks-gym-website-aus-cyber-attack/107007986
8 月 10 日（周一），扎克伯格发布了一篇 6500 字的宣言，主题是个人 AI，主要讲 Meta AI 正在建的「个人超级智能」有哪些可能性。
它更像是扎克伯格在描述自己为什么对 AI 改变社会感到兴奋。可问题在于，他每试图描绘一幅美好图景，就顺手提醒了读者一遍这件事可能怎么出错。
举两个文中被拿出来分析的例子：
扎克伯格写道，每个人都会拥有一个各科都有博士学位、耐心无限的私人导师和教练。
Brandom 的回应是：这个产品已经存在了，就是 ChatGPT、Claude、Gemini。这些工具想学东西时确实好用，但它们在教育场景里的主要用法是躲开学习。而且（在他写这篇文章时）由于缺乏稳健的水印系统，老师无法确认哪些论文是 AI 写的。
扎克伯格设想：如果只有一个人有超级智能律师，那不公平；但如果所有人都有，正义就会被更公平高效地实现。
Brandom 认为这个例子被预设过了——它也可能只是给本已官僚化的系统再加一层复杂度，或者放出一大波用「法律版垃圾邮件」堵塞流程的滥诉者。
扎克伯格提到会有一种动态拍卖机制，保证每个人都以最低价格拿到算力。
但每一个消费级 AI 产品都会把终端用户和算力现货价隔开，是有原因的——浪涌定价是糟糕的用户体验，尤其当这个工具是你吃饭的家伙时。
https://www.meta.com/thefutureisforeveryone/
https://techcrunch.com/2026/08/10/mark-zuckerbergs-ai-manifesto-is-exactly-why-people-dont-like-ai/
AI 的成本正在从科技公司的资产负债表溢出到别人的生活里。
内蒙古乌兰察布凭冷凉气候、低电价和充足土地，吸引了华为、阿里、腾讯、百度、字节及 DeepSeek 等 89 个数据中心项目落地，总投资超 5000 亿元。但该市人均水资源仅 484 立方米，不足全国平均的四分之一，部分旗县已经封井限采。
数据中心的蒸发冷却耗水量巨大，已经和当地牧民的用水产生冲突。
https://x.com/dcbruck/status/2087255279402443079
