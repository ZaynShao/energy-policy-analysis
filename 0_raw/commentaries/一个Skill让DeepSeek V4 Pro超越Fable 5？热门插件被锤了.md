---
title: 一个Skill让DeepSeek V4 Pro超越Fable 5？热门插件被锤了
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/_lCFC9a-FJqD6jdl0K220Q
date_published: '2026-08-19'
fetched_at: '2026-08-20T07:31:10+08:00'
source: wewe-rss
---

# 一个Skill让DeepSeek V4 Pro超越Fable 5？热门插件被锤了

一个 Skill，就能让 DeepSeek V4 Pro 超过 Fable 5？
前两天，J-Space 凭借一组夸张的测试结果迅速刷屏，没想到今天就彻底翻车。
作者宣称，只需将一份 Skill 接入 Agent 环境，V4 Pro 就能在多个基准上大幅提升，部分成绩甚至超过 Fable 5，速度和 Token 效率也能提高两倍以上。
但是社区复测的结果完全相反，非但没提高成绩，还花了更多 token。
面对网友质疑，作者不仅没有公开完整的评测记录或者运行日志，还被曝删除质疑 issue。
至此，一场狂欢变成了公开打假。
一个 Skill，让V4 Pro超过Fable 5？
这次引发关注的项目叫 J-Space Cognition Suite V3.6。
根据项目介绍，这是一套模型无关的推理时控制方案。它不修改模型权重，也不要求微调，而是以 Skill 的形式加入 Agent 运行环境。
《DeepSeek V4 × J-Space 能力释放报告》：https://github.com/Tiger3807861189/DeepSeek-V4-J-Space-Capability-Realization-Report
项目作者将 Agent 常见的失控归纳为四种情况。
第一种是工作集过载。任务同时塞进太多目标、限制和工具信息，真正重要的内容反而被淹没。
第二种是表征漂移。一个名称、数值或者任务目标，在多轮推理和多个文件之间逐渐发生变化。
第三种是无效重试。工具调用失败后，模型没有保留诊断信息，只是沿着原来的路线再跑一遍。
第四种是过早完成。模型生成了一段看起来很流畅的回答，便误以为任务已经结束，却没有验证结果是否真的可用。
这些问题在长程 Agent 任务中尤其常见。
J-Space 试图把整个执行过程组织成一套更加稳定的循环：短判断、执行操作、深入推理、验证结果，遇到问题后再带着诊断信息恢复。
它还会限制当前工作区中同时保持活跃的内容，把关键目标、已经验证的信息、尚未解决的问题和下一步操作写入外部账本。
简单来说，J-Space 希望阻止模型在工作过程中忘记自己到底在做什么。
思路听起来不复杂，公布的成绩却相当惊人。
报告声称，接入 J-Space 后，V4 Pro 的 Terminal Bench 成绩从 87.9 提高到 90.1，NL2Repo 从 61.5 跃升至 73.4，DeepSWE 从 62.7 提高到 72.0。
按照报告中的公开成绩对比，V4 Pro 在部分 Agent 与编程基准上甚至超过了 Fable 5 和 Opus 4.8。
打假反被删帖
最早的负面结果来自来自 J-Space 仓库的 Issue #10。
链接：https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/10
一位开发者使用 V4 Flash 进行了两轮 A/B 测试，覆盖数学推理、代码生成、仓库开发和中断恢复等任务。
在第二轮实验中，对照组和 J-Space 组分别运行 3 次，总计 12 次。
结果显示，两组最终任务完成度没有明显差异，而 J-Space 组却消耗了更多资源。
第三方盲评中，对照组平均得分为 8.30，J-Space 组只有 7.87。
这份实验规模有限，使用的也是 V4 Flash 和自定义任务，无法覆盖 J-Space 报告中的全部基准，但也引起了一些对「性能、速度和 Token 效率同时提升」的质疑。
随后，更实锤的结果出现了。
链接：https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/26
用户 Jyleaves 在 Issue #26 中表示，自己使用 8 张 NVIDIA H20 部署 V4 Flash，并通过 DeepSeek Harness Standard 模式加载 J-Space。
89 道题中，模型通过 69 道，最终得分为 77.5%。而 J-Space 报告给出的对应成绩是 87.1%。
测试者还表示，失败任务至少重新运行了 3 次，依然没有得到报告中的提升，并据此质疑项目数据的真实性。
因此，测试者要求作者公开完整评测环境、测试流程和样本输出。
更火上浇油的是，有开发者在 Issue #23 中称，自己此前发布的质疑 Issue 遭到作者删除，因此只能重新发帖备份。
链接：https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6/issues/23
欲盖弥彰，不打自招。
精准踩中 V4 Pro 痛点
高明的伪装很少凭空编造，只要擅于借用已经存在的事实，一切都会显得顺理成章。
J-Space 恰好踩中了 V4 Pro 最受关注的问题：对外部运行环境过于敏感。
从一开始，大家就发现 V4 Pro 在不同用户和不同调用条件下，表现差了很多。
有人在正式版发布当晚，用相似提示两次测试 3D 直升机游戏。凌晨 0 点 50 分，模型生成的结果还非常粗糙；不到四小时后，它却交出了一个完整得多的项目。
网友猜测差异可能来自模型之外，比如 Harness。
在一个名为 Project2 的工程任务中，同一个 V4 Pro 运行在 DeepSeek Harness 的 Standard 模式下得到 91 分，PTC 模式为 92 分，换成工具更少的 Minimal 模式后，两次测试分别达到 99 分和 96 分。
模型和任务没有改变，外部运行环境却带来了接近 8 分的差距。
随后就出现了一些针对性的方案。
Routing Suite 尝试根据任务类型选择推理模式，避免模型面对简单任务过度思考、遇到复杂任务又过早行动。
GitHub：https://github.com/yjh051108/dsh-routing-suite?utm_source=chatgpt.com
Anchored Standard 则把注意力放在第一次模型请求上：首轮先使用简短提示和少量工具，让 V4 Pro 进入相对稳定的轨迹，随后再开放完整工具能力。
GitHub：https://github.com/xiaobright/dsh-anchored-standard?utm_source=chatgpt.com
这就是 J-Space 最具迷惑性的地方，它借用了一个真实存在的问题。
沿着这套逻辑继续向前，可以让一张「超过 Fable 5」的表格在几分钟内传遍社区，但验证它却没那么容易。
能被复现的提升才叫提升，拿不出过程的结果，数字越惊人，越应该先打一个问号。
参考链接：
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
