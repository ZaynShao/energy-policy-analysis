---
title: RIP：只活了292天的Atlas
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/-vgZFtSke2eY4jC6PiNBPw
date_published: '2026-08-10'
fetched_at: '2026-08-14T07:35:40+08:00'
source: wewe-rss
---

# RIP：只活了292天的Atlas

8 月 9 日，OpenAI 的 AI 浏览器 ChatGPT Atlas 正式走到了生命周期终点。
从 2025 年 10 月 21 日发布，到 2026 年 8 月 9 日停止工作，Atlas 一共存在了 292 天。不到一年，这款一度被视为 OpenAI 正面挑战 Chrome 和 AI 浏览器生态的产品，就结束了自己的独立浏览器生涯。
不过，OpenAI 放弃的只是 Atlas 这一产品形态，并不是浏览器 Agent 本身。Atlas 所探索的能力，正在转向 ChatGPT 桌面应用、Chrome extension/sidebar，并继续与 ChatGPT、Codex 整合。
Atlas 和当时出现的许多 AI 浏览器一样，试图重新设计人与浏览器的交互方式。
用户可以直接在地址栏向 ChatGPT 提问；Ask ChatGPT sidebar 能读取当前网页，进行总结、分析和写作；Browser Memories 可以基于浏览历史保留上下文；Agent Mode 则进一步获得操作能力，可以打开标签页、点击、输入，并执行购物、预约、研究等多步骤任务。
在底层架构上，OpenAI 仍然使用 Chromium，但另外构建了 OWL（OpenAI Web Layer），将 Chromium browser process 与使用 SwiftUI、AppKit、Metal 重建的原生界面分离。
因此，Atlas 的目标从一开始就不只是「给浏览器加一个 AI 助手」，而是让 ChatGPT 直接参与浏览、理解上下文，并进一步操作网页。
但产品上线后，OpenAI 很快遇到了一个更基础的问题：做一款完整浏览器，远不只是做 AI。
10 月下旬，OpenAI 陆续修复日韩 IME、历史记录删除确认、1Password、扩展按钮和弹窗等问题；11 月又加入垂直标签页、Google 默认搜索、扩展导入和 iCloud Passkeys。
进入 2026 年后，Atlas 继续补齐网站数据迁移、Tab Groups、Auto Search、Saved Prompts、DevTools、多 Profile 等能力。
这些更新反映出，维护一款浏览器意味着 OpenAI 不仅要解决模型和 Agent 的问题，还必须处理扩展、密码、Cookies、登录、输入法、开发者工具、安全更新等大量成熟浏览器早已具备的基础能力。
与此同时，Atlas 最核心的 Agent 体验也并不稳定。
The Verge 在早期测试中发现，Atlas 在搜索结果、地点理解和 Agent 执行速度上都存在不稳定情况。一次 Amazon 加购任务中，Atlas 大约耗时 10 分钟，而同一测试里的 Perplexity Comet 约为 2 分钟。
后续多款 AI 浏览器的横向测试也显示，只要任务流程变长，Agent 往往仍然需要用户持续检查和干预。换句话说，它已经可以代替用户执行部分操作，但距离真正可靠地「接管任务」还有明显距离。
安全问题则更加根本。
浏览器 Agent 一方面可以读取网页内容，另一方面又可能在用户已经登录的网站中执行操作。这让 Prompt Injection 的风险比普通聊天机器人更直接。
恶意指令可以被隐藏在网页、邮件或其他内容中。如果 Agent 无法准确区分「用户真正下达的指令」和「网页试图诱导模型执行的指令」，就可能在用户不知情的情况下采取操作。
OpenAI 在 Atlas 发布时就承认，这类攻击无法被完全阻止。2025 年 12 月，公司又公开了一套利用强化学习训练攻击与防御模型的方法，并表示 Prompt Injection 可能是一个需要多年持续解决的问题。
直到 2026 年 Black Hat 前夕，Zenity 的研究仍然能够诱导部分 AI 浏览产品操作登录状态下的 WhatsApp 和 Amazon 页面。不过，研究同时认为，在被测试的产品中，Atlas 设置了相对更多的安全边界。
除了可靠性和安全性，Atlas 还有一个更现实的问题：平台覆盖始终有限。
产品发布时仅支持 Apple Silicon Mac。OpenAI 曾表示 Windows、iOS 和 Android 版本随后会推出，但直到停服，Atlas 都没有形成完整的公开多平台版本。
这对于一款试图挑战主流浏览器的产品尤其不利。
更麻烦的是，Atlas 面对的还是拥有巨大存量用户的 Chrome 和 Edge。Google 和 Microsoft 可以直接在现有浏览器中叠加 AI 能力，而 Atlas 必须先说服用户进入一个新的浏览环境。
而用户更换浏览器，意味着迁移书签、扩展、密码、Cookies、登录状态，以及多年形成的使用习惯。新的浏览器不仅要「更好」，而且必须好到足以抵消这些迁移成本。
截至 2026 年 7 月，StatCounter 数据显示，Chrome 的全球市场份额仍为 68.22%，Safari 为 16.47%，Edge 为 5.37%。Atlas、Comet、Dia 等产品甚至尚未进入主要浏览器的独立统计分类。
进入 2026 年后，Atlas 的更新重点逐渐集中到 Agent、记忆和工作流。1 月加入 Tab Groups 和 Auto Search；2 月增加 Saved Prompts、个性化快速动作，以及根据 Browser Memories 自动整理标签页的能力；2 月 24 日，官方还专门优化了 Agent 在长任务中的持续执行能力。
3 月 10 日，Atlas 发布 Build 1.2026.63.7，这也是官方 Release Notes 中最后一条公开功能更新。4 月，媒体开始报道 OpenAI 计划进一步整合 ChatGPT、Codex 和 Atlas。
7 月 9 日，OpenAI 正式宣布 Atlas 下线，并提供约 30 天迁移期。
8 月 9 日，Atlas 停止工作。
OpenAI 至此结束了这次独立 AI 浏览器实验，但 Atlas 所代表的问题并没有因此结束。
AI 浏览器一度火热，大致形成了两类路线。
一类是 Atlas、Comet、Dia、Neon、Fellou 这样的独立产品。
图源：Medium
它们的共同思路，是从浏览器本身重新设计 AI 交互。AI 不再只是一个附着在网页旁边的侧边栏，而是能够读取当前页面、理解多个标签页、记住浏览上下文，并进一步替用户点击、填写和执行任务。
Perplexity 的 Comet 是目前相对完整的代表之一。它已经覆盖 Mac、Windows、iOS 和 Android，并把 Perplexity 原有的搜索与引用能力进一步延伸到邮箱、购物、研究、旅行等浏览场景。
Dia 更强调网页、标签页和工作上下文之间的连接，而不是单纯追求 Agent 自动操作。2025 年 9 月，Atlassian 以 6.1 亿美元现金收购 The Browser Company，此后 Dia 继续向 knowledge work browser 的方向发展。
Opera Neon 和 Fellou 则更强调任务执行。Neon 将 Tasks、Agent 和代码生成放进浏览器；Fellou 主打 Deep Action、自动研究以及可编程的 Agent workflow。
这条路线的优势很直接：既然 AI 需要理解网页、标签页、Cookies、登录状态和用户正在进行的任务，那么从浏览器这一层开始设计，理论上可以获得更完整的上下文，也更容易把 Agent 做成浏览体验的一部分。
但 Atlas 的经历已经说明，从零维护一款浏览器，本身就是一项远超 AI 功能开发的工程负担。更重要的是，独立 AI 浏览器还必须跨过另一道门槛：用户为什么要换浏览器？
对于已经拥有稳定浏览习惯的人来说，迁移成本是真实存在的。因此，新的 AI 浏览器不能只是比原有浏览器「多几个 AI 功能」，而必须提供足够大的体验跃迁，才能让用户愿意重建自己的浏览环境。
这也是独立 AI 浏览器面临的结构性挑战。
另一类是 Chrome、Edge、Brave、QQ 浏览器和 360 这样的存量浏览器 AI 化。
Google 把 Gemini 集成进 Chrome，并继续加入多标签理解、Google Apps 上下文和自动浏览能力。
Microsoft 在 Edge 中推进 Copilot Mode。
Brave 在现有浏览器基础上测试 Agentic Browsing，QQ 浏览器和 360 AI 浏览器也都采用了类似思路，在原有产品上增加 AI 搜索、网页理解和 Agent 能力。
相比重新做一款浏览器，这条路线最大的优势，是用户几乎不需要付出迁移成本。原有的扩展、密码、账户体系和工作流都可以保留，AI 能力只需要逐步叠加在既有产品之上。
这也让一个问题越来越明显：用户真正需要的，到底是一款「AI 浏览器」，还是浏览器里的 AI？
如果核心需求只是总结网页、跨标签查询、辅助搜索和写作，那么侧边栏、插件或者浏览器原生功能已经可以完成大部分工作。即使进一步进入 Agent 阶段，AI 可以点击网页、填写表单和完成跨站任务，这些能力也并不天然要求用户安装一款全新的浏览器。
因此，独立 AI 浏览器真正需要证明的，不是「浏览器里可以放 AI」，而是它能够提供一些存量浏览器很难通过叠加 AI 功能实现的体验。
例如，更完整的长期上下文、更深的任务管理，或者围绕 Agent 从底层重新设计标签页、权限和工作流。
Atlas 没有证明这一点足以让大量用户迁移，但 Comet、Dia、Neon 等产品还在继续尝试。
目前来看，AI 进入浏览器几乎已经成为共同方向。
你平时会使用 AI 浏览器吗？
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
