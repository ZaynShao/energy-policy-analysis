---
title: AI 时代的编程语言，这次是来自中国的底层创新
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/FG_-DEwSw0_ubBE36tMeeA
date_published: '2026-07-09'
fetched_at: '2026-07-11T07:31:57+08:00'
source: wewe-rss
---

# AI 时代的编程语言，这次是来自中国的底层创新

AI 对软件行业最直接的影响，是重塑整个软件工程链路。当所有开发工具都在走向 AI 原生化，编程语言作为软件生产的入口，自然也值得重新审视。
OpenAI 联合创始人 Greg Brockman 也曾写道：“Rust 是代理的完美语言，因为如果它能编译通过，它就几乎是正确的”。
近期知名高性能开源项目 Bun 将核心代码大规模重写为 Rust ，则给出了一个更具体的产业信号：当 AI 降低迁移成本之后，软件基础设施正在重新向更强约束、更高性能、更易被机器检查的语言迁移。但 Rust 毕竟诞生于生成式 AI 爆发之前；其核心设计目标是安全的底层编程，而非 Agent 之间的高效协作。OpenAI 创始团队成员 Andrej Karpathy （Vibe Coding 概念的提出者）曾在 X 上指出：“LLM 正在彻底改变软件的约束条件，代码迁移、C 到 Rust 的移植、COBOL 等遗留系统升级都会因为 LLM 擅长 “翻译” 而发生变化，但 Rust 本身也远不是面向 LLM 的最优目标语言, 什么样的语言是最适合 AI 的依然是开放式的问题。”
AI 正在改变编程语言的分布，这也引出了一个更值得讨论的问题：有没有一门从一开始就面向 Agent 协作、快速反馈和工程闭环设计的新语言？
这个问题已经不只是产业观察，也进入了软件工程研究界的评测体系。量子位近日报道了一篇关于 “冷门新语言 AI 写不动” 的论文，MoonBit 正是在这里进入我们视野。
论文题为《No Resource, No Benchmarks, No Problem? Evaluating and Improving LLMs for Code Generation in No-Resource Languages》，被 IEEE Transactions on Software Engineering 接收。
它把 MoonBit 和 Gleam 放进 “no-resource programming languages” 的框架下评测：两者都足够新，公开代码、教程和问答样例还不足以让大模型在预训练阶段充分见过；但论文真正有意思的地方，是同样作为 no-resource language，MoonBit 在可见语料更少的情况下，反而在多组设置下比 Gleam 更能从 AI 辅助中受益。论文按 GitHub 仓库规模统计时，MoonBit 约为 Gleam 的七分之一；如果看 2024 年 3 月前模型可能见过的公开仓库，MoonBit 的可见样本更少。
论文中的结论指出，few-shot 和 RAG 这类上下文学习方法在 MoonBit 上带来的提升高于 Gleam，并将原因之一指向 MoonBit 的 AI-friendly 设计；在更难的 McEval-Hard 上，Qwen 2.5 Coder 32B Base 继续预训练后，MoonBit 的 pass@1 达到 25.86%，Gleam 为 12.47%；进一步通过 instruction transferring 迁移指令跟随能力后，MoonBit 达到 32.60%，Gleam 为 26.08%。
可以看到语言设计显著影响模型学习和生成代码的效率，所谓 AI 友好的编程语言并不是一句「营销口号」。
从 2024 年 3 月到现在，MoonBit 的生态也开始给出工程侧证据：Mooncakes（MoonBit 包管理网站）库的数量已跨过万级门槛，累计下载超 400 万次，并出现了 Crater、Golem Cloud 的 Wasm Component 案例、MoonXi-net 和 Choir 等浏览器、云组件、深度学习框架与多 agent 编排样本，MoonBit 生态的快速发展在 AI 时代之前是难以想象的。
更值得注意的是，这套底层技术背后的开发团队来自中国。AI 时代的编程语言是否真的来了？这一次，我们不妨一探究竟。
一、MoonBit 不只是一门编程语言，而是一条内置 “形式化证明” 的软件流水线
但如果把 MoonBit 仅仅当成一门新语言的语法讨论，就错过了它真正特殊的地方。MoonBit 从设计之初就同步构建了编译器、构建系统、包管理器、测试框架、文档工具和 AI 编程助手，形成了一条从代码编写到产物交付的完整流水线。这种 “语言即工具链” 的思路，在 AI 编码时代有直接的工程意义。
1、核心不是一次性生成代码，而是闭环
AI 辅助编程的核心不是单次生成一段代码，而是 “生成 — 编译 — 诊断 — 修复 — 测试” 的闭环。在这个闭环里，编译器给出的反馈能否被模型有效利用，直接决定了 AI 修正错误的效率。MoonBit 的编译器和构建系统一体设计，没有在遗留工具链上打补丁的历史负担，这为快速迭代和清晰的诊断信息提供了架构上的基础。
2、形式化验证纳入原生工具链，被更强约束检查
更值得注意的是，MoonBit 把形式化验证也纳入了原生工具链的设计范畴。这意味着 MoonBit 试图让 AI 生成的代码不仅能编译通过，还能在同一个工具链内接受更强约束的检查。通过定义 Hoare triples 的方式，MoonBit 提供比使用专用形式化证明语言更好的书写体验；AI 可以对代码有选择地证明，同时无需提供完整的证明链条，成功率更高。AI 生成代码的 “可检查性” 会提升一个台阶：模型写出代码，编译器检查类型，验证器检查性质，反馈可以同时来自多个维度。这种设计思路在已有的主流语言中并不多见，因为它要求语言设计者在早期就考虑验证工具与编译器、构建系统的集成，而不是事后以外部工具的形式挂载，而且不同于 Rocq 等学术语言，MoonBit 证明的代码是真实的生产的代码而不是抽取之后的代码。
以二分查找这个经典例子为例。二分查找看似简单，却是出了名的 “容易写错”。Java 核心开发者、 《Effective Java》作者 Joshua Bloch 在 2006 年曾专门撰文指出，Java 标准库中的二分查找实现存在整数溢出 bug，而这段代码在生产环境中运行了近十年才被发现。
上图展示了 MoonBit 中对二分查找的完整验证。左侧是带有合约和循环不变量的函数实现，右侧是谓词定义文件，底部终端则显示验证全部通过。
在 MoonBit 里，形式化验证并不是额外附加的一层文档，而是和代码本身一起构成程序的一部分。
二、AI 原生应用场景：自带沙箱的跨平台部署能力，智能体的理想语言
1、跨平台部署能力，降低 AI 生成代码进入真实环境时的兼容成本
Skill 是当前 Agent 生态中一个已经存在的概念：它通过 SKILL.md 文件为 AI Agent 提供专门的指令和工作流，让 Agent 在特定任务中知道该怎么做。但 SKILL.md 本身只是文本，真正让 Agent 完成复杂工作的，是背后那层可执行代码。
MoonBit 试图补上这层可执行能力。开发者可以用 MoonBit 编写异步逻辑，编译成 Wasm 字节码，通过 Mooncakes 发布，最终用户或 Agent 只需一条命令就能运行。
Wasm 的优势在于可移植、可嵌入、可隔离。同一份逻辑可以进入云函数、边缘节点、浏览器、插件系统，也可以进入 Agent runtime，作为一段受控能力被调用。对 Agent 来说，这一点尤其重要：它需要自动执行代码，但又不能无条件信任代码。
以已经发布在 Mooncakes 上的 peter-jerry-ye/hn-brief 为例，这个工具会抓取 Hacker News 当日热门文章和高赞评论，调用 DeepSeek 模型生成中文简报。用户只需要执行：
这条命令背后，moon 工具链会解析 Mooncakes 包坐标，获取对应的 Wasm 产物，在本地 Wasm 运行环境中启动程序，并把结果返回给用户。使用者不需要再为每个 Skill 单独配置 Python、Node 或其他运行环境。
2、原生的沙箱模型，让 MoonBit 天然适合隔离执行场景。
如果说 Wasm 和 Mooncakes 解决的是 “代码怎么跑”，那么运行时策略解决的是 “代码能跑什么”。
每个 Skill 可以附带策略文件，声明它需要哪些环境变量、允许访问哪些网络端点。以 hn-brief 为例，它只允许访问 Hacker News 和 DeepSeek 两个地址，并要求宿主环境提供 DEEPSEEK_API_KEY：
运行时通过 --experimental-policy 加载策略后，程序的网络访问会受到约束。如果移除 DeepSeek 的端点，请求会被拒绝，而不是默认放行。
这种机制的价值不在于提供一个不可攻破的安全沙箱 —— 它远未达到操作系统级隔离的程度，也不能证明密钥不会被已获授权的端点转发 —— 而在于把程序对外部资源的依赖变成了一份显式、可审计的声明：这个 Skill 要访问哪里、需要什么环境变量、能不能读写文件，都可以提前看到。对 Agent 场景来说，这比盲目运行一段脚本更可控。
3、不只是 AI Coding 的目标语言，也被用于 AI 基础设施本身
更值得注意的是，MoonBit 的应用并不只停留在 “让 AI 更容易写代码”。从已有案例看，Crater、Golem Cloud 的 Wasm Component 案例、MoonXi-net 和 Choir 等项目，已经覆盖浏览器、云组件、深度学习框架和多 Agent 编排等方向。
这些场景需要的是可分发、可嵌入、可约束执行的软件组件。也就是说 MoonBit 一边可以成为 AI coding 的目标语言，另一边也可以成为 Agent runtime、云端组件、浏览器侧智能应用里的实现语言。
所以，MoonBit 在 Agent 场景中的价值不是单点的。它给出的是一条完整链路：用一门支持异步并发的语言写逻辑，编译成跨平台 Wasm，通过 Mooncakes 分发，再用策略文件约束运行行为。这个链条的大部分环节可能不是 MoonBit 首创的，但把它们垂直整合放进同一个工具链里，才是它真正值得关注的地方。
三、AI 时代原生编程语言的后发优势与边界
新语言刚出来的时候，总给人一种 “生态不够、案例少、开发者不买账” 的印象。但在 AI 时代，这件事也开始呈现出另一面：没有太多历史包袱，反而意味着它可以围绕新的软件生产方式重新设计自己。MoonBit 的后发优势正在于此：它可以从一开始就把 AI 友好、快速反馈、可验证性和多后端部署放进语言与工具链设计中。
在 AI Coding 场景下，一门语言的竞争力不再取决于人类程序员的学习曲线，还取决于模型是否容易生成可靠、可用的产物。而模型要高效地生成正确的代码，取决于编译器是否能给出清晰诊断，测试和验证是否能快速接入；代码要真实可用，取决于产物是否能面向不同运行环境稳定分发。MoonBit 试图做的，正是把这些环节放进同一个工程闭环：生成、编译、诊断、修复、测试、验证，再到多后端输出和包管理以及分发。
上述公开论文中的结果也给出了一个值得关注的信号。在公开语料少于 Gleam 的情况下，MoonBit 反而更能从 few-shot、RAG、继续预训练和 instruction transferring 等方法中受益。这说明，模型学习一门语言的效率，并不只由语料规模决定，也会受到语言设计、工具链反馈和代码模式一致性的影响。
这对新语言来说很关键。过去，新语言最大的门槛往往是生态冷启动，开发者也缺少足够理由迁移。但现在，AI 正在压缩这个积累周期。原本高度依赖人工和社区时间的工作，正在变得更快。
当然，AI 不会去掉工程门槛。生态成熟度、工业验证、开发者心智和长期维护能力，仍然是一门语言能否走远的核心问题。因此，AI 时代并不会让新语言 “自动成功”，但是会削弱一部分传统生态壁垒，把竞争重新拉回到语言和工具链本身。真正有机会的新语言，必须同时回答三个问题：模型能不能高效学会，生态能不能快速长起来，开发者愿不愿意在真实项目中采用。
从这个角度看，MoonBit 的价值不只是 “又一门新语言”。它更像是在回答一个新的基础软件问题：当代码开始由人和 AI 共同生产时，一门语言应该如何设计自己的语法、工具链、验证能力和部署路径。对于 AI 时代的编程语言来说，这可能才是更关键的起点。
参考链接
[1] Andrej Karpathy on X: “LLMs change the whole constraints landscape of software completely”
https://x.com/karpathy/status/2023476423055601903
[2] Greg Brockman on X: “rust is a perfect language for agents, given that if it compiles it's ~correct”
https://x.com/gdb/status/2007228511363444905
[3] Bun PR #30412: Rewrite Bun in Rust
https://github.com/oven-sh/bun/pull/30412
[4] 量子位：《冷门新语言 AI 写不动？IEEE 论文：从零到及格线，MoonBit 给出完整训练路线》
https://mp.weixin.qq.com/s/Ma_y7a5TNbJy64YK2Fh74Q
[5] Alessandro Giagnorio, Alberto Martin-Lopez, Gabriele Bavota. “No Resource, No Benchmarks, No Problem? Evaluating and Improving LLMs for Code Generation in No-Resource Languages.” arXiv:2606.16827, accepted by IEEE Transactions on Software Engineering.
https://arxiv.org/abs/2606.16827
[6] CSDN：《MoonBit 生态跨过万级门槛：开发者开始用它做浏览器、云组件、智能体和深度学习框架》
https://mp.weixin.qq.com/s/N2Sr9s0vO0sa6Fo3fy0_oQ
[7] 《当 AI 主宰写代码，MoonBit 嵌入「形式化验证」让 Bug 清零》
https://mp.weixin.qq.com/s/CMh66hhpMVbKvwvnonWPRg
[8] MoonBit 包管理网站
https://mooncakes.io/
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
