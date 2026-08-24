---
title: DeepSeek终于长出“眼睛”，V4 Flash视觉模型上线
source_account: 腾讯科技
source_url: https://mp.weixin.qq.com/s/qFO1Ho9-3b7In6pn_KwtQA
date_published: '2026-08-21'
fetched_at: '2026-08-25T07:35:30+08:00'
source: wewe-rss
---

# DeepSeek终于长出“眼睛”，V4 Flash视觉模型上线

文｜晓静
编辑｜徐青阳
8月21日下午，DeepSeek官方API文档的“模型细节”页面出现一个新的模型：deepseek-v4-flash-vision-exp，模型版本标注为 DeepSeek-V4-Flash-Vision-Exp。
从官方页面披露的信息看，这是DeepSeek V4系列首个直接支持图片输入的视觉模型。它拥有1M上下文，最大输出长度384K，支持JSON Output、Tool Calls、Responses API、Anthropic API以及对话前缀续写，图片将按照尺寸折算成Token，与文本Token一同计费。
V4 Flash Vision Exp目前显示的API价格与Flash完全一致：缓存命中价格在空闲和高峰时段分别为0.05元和0.10元/百万Token，缓存未命中分别为1.5元和3元，输出分别为4.5元和9元。
从时间上来看，在DeepSeek刚刚开源自己的Agent Harness一周后，视觉能力迅速接入Harness，让此前相对独立的模型、图片、文件、工具和Agent执行链开始连在一起。DeepSeek正在补齐一套Agent系统最基础的感知入口。
01
一周前，DeepSeek还“看不见”图片
4月下旬，DeepSeek发布V4预览版，包括V4-Pro和V4-Flash两个版本。V4-Pro总参数量1.6T、激活49B，V4-Flash总参数284B、激活13B，两者统一支持1M上下文。当时的升级重点放在Agent、推理和长上下文上，并没有公布视觉输入能力。
8月13日，DeepSeek进一步更新V4-Pro，并在随后开放DeepSeek Harness。Harness试图把模型、工具、技能、会话、沙箱、存储和Agent Loop放进一套可组合的运行框架中。
但一个非常实际的问题很快暴露出来：DeepSeek自己的模型没有视觉能力。
过去一周，在DeepSeek Harness的GitHub讨论区里，“怎么让DeepSeek看图”已经成为一个高频问题。
有开发者上传图片时，Harness会直接返回：MODEL_DOES_NOT_SUPPORT_IMAGES
原因是V4 Flash和V4 Pro在模型目录里都被声明为纯文本模型，输入模态只有text。图片甚至无法进入会话，后续Agent自然也无法调用工具处理图片。
于是社区开始自己给DeepSeek“装眼睛”。
一种方案是在DeepSeek前面再接一个Qwen-VL等视觉模型，先把图片转换成文字描述，再把文字交给DeepSeek推理；另一种方案则尝试修改Harness，让图片先保存到工作区，再由视觉插件、脚本或者子Agent读取。
过去几天，GitHub上已经出现多个类似的vision bridge插件。开发者甚至专门做出了dsh-deepseek-vision：图片先交给其他视觉语言模型理解，再把描述传给DeepSeek。
这形成了一个略显尴尬的局面。
DeepSeek刚刚发布了一套高度插件化的Agent Harness，Agent已经能够调用终端、文件、代码和外部工具，但面对最常见的截图、网页图片和报错界面时，仍需要借用其他公司的模型。
V4 Flash Vision Exp的出现，开始补上视觉能力。
02
先改Harness，再放出模型
回头看，DeepSeek对视觉能力的准备其实已经提前写进了Harness。
DeepSeek Harness最新rc.8版本的Release Notes明确增加了一项功能：“增强多模态支持度，DeepSeek模型适配器支持配置启用原生图片请求。”
与此同时，/goal、/plan等命令开始支持图文输入，@菜单能够引用文件和会话；官方还修复了图片尺寸过大、历史图片载荷过高导致模型请求失败等问题。
这个变化刚出现时，很多开发者首先想到的是：DeepSeek自己的视觉模型是不是要来了？
8月21日下午，开发者在Harness相关代码和配置中发现了deepseek-v4-flash-vision-exp这一模型名称。
03
一个和V4 Flash同价的视觉模型
目前公开信息还不足以判断V4 Flash Vision Exp究竟采用什么模型架构。DeepSeek没有公布参数规模，也没有发布技术报告和视觉Benchmark。
DeepSeek此前已经有一条独立的DeepSeek-OCR产品线，而截至7月底，普通V4 Flash的公开API仍明确只支持文本输入，OCR与V4也属于不同模型体系。这意味着，Vision Exp存在一种合理的可能：DeepSeek并没有重新训练一个从底层统一处理文本和视觉的V4 Flash，而是把已有的视觉编码、OCR或图像理解模块接到了V4 Flash之前，再由后者完成推理和生成。如果是这种架构，它与Gemini、GPT这类更强调统一多模态训练的模型仍有区别。
当天稍早的开发者实测也留下了一个有意思的细节：deepseek-v4-flash-vision-exp最初接收image_url时仍返回expected 'text'，随后官方模型表和视觉接口才陆续更新。这至少说明，视觉能力与V4 Flash现有API体系之间经历了明显的适配过程。
不过，这些现象都只能作为线索，不能直接证明底层架构。DeepSeek目前没有公布Vision Exp的模型结构、训练方式或视觉编码器信息，因此仅凭“现在可以直接上传图片”，还无法判断它究竟是原生多模态模型，还是一套视觉前端与V4 Flash组合起来的系统。
但从产品设计中，已经能够看出几个值得注意的信号。
首先，它被放进了V4 Flash产品线，而不是V4 Pro。这意味着DeepSeek现阶段首先选择将视觉能力接入更小、更快、更便宜的模型。
V4 Flash本身只有284B总参数、13B激活参数，定位就是高吞吐、低成本。如果Vision版本延续这一定位，它瞄准的很可能不是单纯的图片聊天，而是大量发生在Agent里的视觉任务。
例如读网页截图、识别报错界面、分析图表、查看软件UI、读取设计稿，再根据图片继续操作电脑或者修改代码。
这些任务对“单次图片理解达到最强”未必有极端要求，却非常在意速度、价格以及能否连续运行。
第二个信号来自定价。
根据DeepSeek当前官方页面，V4 Flash Vision Exp的价格没有因为加入视觉能力而上涨。
高峰时段，缓存未命中输入仍为3元/百万Token，输出9元；空闲时段则分别只有1.5元和4.5元。图片不会采用单独的“每张图片”收费方式，而是根据尺寸转换成Token，再与文本Token统一计费。
这与DeepSeek此前的产品逻辑高度一致：尽量把新能力压进现有Token计价体系。
如果正式版继续维持这一策略，视觉理解可能再次进入DeepSeek熟悉的价格战区间。
但现在还不能简单比较“看一张图多少钱”。真正的成本取决于DeepSeek如何把不同尺寸图片换算成Token，目前需要等待官方完整的图像Token计算规则。
第三个信号是它仍然带有明确的 Exp 后缀。
DeepSeek此前也使用过类似路线。
2025年9月，DeepSeek先推出V3.2-Exp，用实验版本验证新的DSA稀疏注意力机制；两个月后再升级到V3.2正式版。DeepSeek后来明确表示，实验版获得了大量社区对比测试结果，这些反馈帮助验证了新架构。
Vision Exp很可能承担类似角色：先把模型交给开发者，在真实图片和Agent工作流中寻找问题，再决定最终版本。
推荐阅读
