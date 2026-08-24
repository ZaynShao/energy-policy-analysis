---
title: WorkSwarm让Agent组队干活，JiuwenBox安全沙箱守护每一步执行
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/ACQ7ff-Vj0hGC3QLNHXsbg
date_published: '2026-08-20'
fetched_at: '2026-08-25T07:36:31+08:00'
source: wewe-rss
---

# WorkSwarm让Agent组队干活，JiuwenBox安全沙箱守护每一步执行

办公智能体的能力边界正在快速外扩。就在上周，openJiuwen（由华为 2012 实验室、华为云、终端、计算联合构建）将旗下的蜂群智能体升级为 WorkSwarm 蜂群办公智能体：AI 不再只是聊天框里的问答助手，而是一支分工协作的团队。
能力越强，另一个问题就越难回避：当 AI 真的伸出 "手" 去动用户的电脑，谁来保证它不越界？
openJiuwen 给出的答案是 JiuwenBox：一个跨平台、多等级的 Agent 安全沙箱。
Agent 要执行的命令、要运行的代码、要读写的文件，不再直接落进用户的电脑，而是先送进 JiuwenBox 隔出来的 "隔离房间" 里安全地跑完，再把结果交回来。
与其盯着 AI 的每一步，不如提前给它划好活动范围 —— 这就是 JiuwenBox 要干的活。
一、JiuwenBox 是什么
JiuwenBox 的定位，可以用一个比喻说清：给 AI 干活的临时房间。
每个任务单独开一间房，房间之间互相看不见、碰不到；
房里有自己的一套文件视角和网络视角，Agent 能看什么、碰什么，由用户说了算；
任务一结束，房间直接拆掉，不在电脑上留下任何残留。
它和 WorkSwarm 是这么配合的：用户在 WorkSwarm 里发一个任务，Agent 负责把任务想清楚、拆成几步；每一步要跑的命令、要运行的代码、要碰的文件，统统送进 JiuwenBox 的沙箱去执行。Agent 负责 "出主意"，沙箱负责 "安全地动手"。
用户└→ WorkSwarm (Agent 想清楚要做什么)└→ 执行命令 / 运行代码└→ JiuwenBox 沙箱 (安全地把事办成)├→ 把结果交回来└→ 房间拆掉，不留痕迹
二、一套统一 API，三层架构
从架构上看，JiuwenBox 整体分三层。
接入层：接待来点单的人。目前是 WorkSwarm Agent 和 JiuwenBox CLI，以后第三方的 Agent 也能按标准协议接进来。
管理平面：统筹全局。谁进谁出、按什么规矩办、每笔账怎么记，都在这层定。
运行时：真正动手干活的地方。命令在这跑、文件在这读写、网络在这进出。
图 1：JiuwenBox 总体架构
管理平面里有哪些 "主管"
Sandbox Manager：沙箱总管。创建、启动、停止、重启、销毁，还有命令执行、文件上下传，都是它管。
Policy Engine：管 "规矩"。安全策略写在哪、怎么合并生效，都由它定。
Audit Logger：负责记账。谁在什么时候干了什么、成没成功、花了多久，一清二楚，可以留存备查。
Interface Authentication：负责看门。设了访问凭证（Token）之后，没带凭证或验不过的一律拦在门外。
三种不同的 "房间" 等级
JiuwenBox 支持三种隔离强度，覆盖不同平台与安全等级：
Linux 任务级沙箱：最轻量，秒开秒关，适合日常跑命令、跑代码。
Windows 沙箱：Windows 平台上的对应方案，能力与 Linux 版对齐。
微虚机沙箱（开发中）：安全性比上述两种沙箱都要高，每个沙箱是一台独立的迷你虚拟机，哪怕里面出了天大的问题，也翻不出这台虚拟机的墙。
三、它到底安全在哪
隔离机制是沙箱产品的核心，底层技术不少，但思路可以用大白话讲明白。
Linux 任务级沙箱：层层上锁
它的思路不是 "装一道铁门"，而是 "上六道锁，一道比一道细"：
换身份：沙箱里的程序都以一个低权限的 "临时用户" 身份运行，拿不到宿主机的管理员权限。就算它在里面想办法 "提权"，升到的也是假身份，碰不到真系统。
隔房间：每个沙箱的进程、通信、网络标识都是独立的一套，这个房间里的程序看不见也摸不着别的房间和你的系统。
管文件：预先定好一份 "能碰哪些文件夹" 的清单，清单之外的地方，想看想写都会被系统直接挡回去。
管动作：默认封掉几十个危险的系统操作，比如调试别的程序、挂载磁盘、重启机器、替换内核这类。这些限制在沙箱启动时就锁死，运行期间改不了。
管网络：可以选 "独立上网"（每个沙箱一套单独网络，能精细控制它连哪些 IP、哪些网站、哪些端口），也可以选 "共用主机网络"（省事，但隔离弱一点）。
管资源：给每个沙箱设内存、CPU、进程数上限，避免一个失控的任务把整台机器拖垮。
Windows 沙箱：用系统自带的安全机制
Windows 上有自己的一套原生安全工具，JiuwenBox 直接拿来做同样的事：
进程隔离：每个沙箱跑在独立的安全上下文里，碰不到你机器上别的程序。
文件权限：用 Windows 的文件权限系统，限制它只能读写你允许的路径。
防火墙：控制沙箱能连出去的地址、端口和协议。
资源配额：限制 CPU、内存、进程数，防止资源被耗尽。
微虚机沙箱：最硬的一道墙
这是三种沙箱里最特别的一种。前面两种沙箱，底层其实还是共用宿主系统的那套内核（操作系统最核心的那层程序）—— 就像大家都在同一栋楼里，靠的是楼内的门锁和保安。万一 "楼体本身" 被攻破了，所有房间的门锁都形同虚设。
而微虚机沙箱，是给每个沙箱配了一台独立的迷你虚拟机，有自己独立的内核。这相当于 "楼里楼"—— 就算里面那栋楼被彻底攻陷，外面这栋楼还是安全的，两层之间是硬件层面划出来的墙。所以它的隔离等级明显更高，适合金融、政务这类对安全要求特别严格的场景。
四、在 WorkSwarm 里，一条命令开启
如果你已经在用 WorkSwarm，沙箱直接通过 /sandbox 这组 TUI 命令管理，不用碰配置文件，也不会打断你和 Agent 的对话。
/sandbox enable # 打开沙箱（需要时会自动拉起 JiuwenBox 并重建 Agent）/sandbox disable # 关掉沙箱/sandbox status # 看一眼当前状态（是否开启、生效的读写路径、排除命令等）/sandbox help # 列出全部沙箱子命令
enable 之后，Agent 执行的所有命令都会自动送进沙箱，Agent 代码一个字都不用改。
在此基础上，还可以做两类精细控制：
放行信得过的命令。 比如版本管理工具 git，可以用 exclude 把它排除在沙箱之外：
/sandbox exclude add "git *" # git 命令直接本地执行，不进沙箱/sandbox exclude list # 看看当前有哪些排除规则/sandbox exclude remove "git *" # 取消这条排除
排除规则用 shell 通配符（glob）匹配，比如 "git *" 能覆盖 git clone、git commit 等一系列 git 操作。
圈定可写路径。 这是最实用的一组命令 —— 你可以精确指定 Agent 能往哪些目录写文件：
/sandbox files allow ./tmp/ # 允许写 ./tmp/（可读可写）/sandbox files deny ./secret/ # 禁止写 ./secret/（仍可读，只读）/sandbox files list # 查看当前生效的读写路径/sandbox files remove ./tmp/ # 撤销某条路径设置
allow /deny 管的是写权限（能不能写），跟传统的文件读写权限不是一个概念。它也支持 "父子嵌套"：比如先 allow /tmp、再 deny /tmp/secret，就能 "整个临时目录随便用，但某个敏感子目录锁死"。反过来（先 deny 父目录、再 allow 子目录）是不允许的，父目录一旦锁死，子目录也会被盖住。
偏好一次配好的用户，也可以在 config.yaml 里声明沙箱设置，让 Agent 启动时自动带上；
sandbox:url: "http://127.0.0.1:8321"type: "jiuwenbox"startup_mode: "internal" # 让 Agent Server 自动管理沙箱进程policy_file: "code-agent-policy.yaml"enabled: trueexcluded_commands:- "git *" # 这类安全命令留在本地跑，不进沙箱
不经过 WorkSwarm 的开发者，则可以直接用 JiuwenBox CLI 创建沙箱、执行命令、上传文件，把它当成一个独立工具使用。
# 开一个沙箱jiuwenbox --base-url ${SANDBOX_URL} sandbox create --sandbox-id mysandbox# 在里面跑条命令jiuwenbox --base-url ${SANDBOX_URL} sandbox exec mysandbox -- python3 -c 'print("hello")'# 传个文件进去再跑jiuwenbox --base-url ${SANDBOX_URL} sandbox upload mysandbox ./script.py /tmp/script.pyjiuwenbox --base-url ${SANDBOX_URL} sandbox exec mysandbox -- python3 /tmp/script.py# 用完删除jiuwenbox --base-url ${SANDBOX_URL} sandbox rm mysandbox --yes
其它常用命令还有 sandbox ls（看列表）、sandbox logs <id>（看日志）、sandbox policy get <id>（看当前策略）等，不一一展开。
示例：模拟用户下载执行网络上的有害脚本，在JjiuwenBox沙箱加持下，所有有害攻击（信息侦察、提权、DoS、文性系统破坏等）均执行失败
五、结语
WorkSwarm 想回答的问题是：AI 能不能像一支团队那样干活。JiuwenBox 的角色，则是为这支团队守住安全边界，让用户敢于放手。
多平台、多等级：Linux、Windows 都能用，还有开发中的微虚机高安全模式，按需选择。
规则自己定：所有安全要求写在一个配置文件里，想放行什么、想拦住什么，你说了算，还能随时改。
和 WorkSwarm 无缝衔接：一条命令就能给 Agent 套上沙箱，代码零改动。
全程留痕：谁做了什么、成没成功、花了多久，都有记录，出了事能查。
用完即走：每个任务一个独立房间，结束就销毁，不留任何残留。
对个人用户，它是一层随手可开的保险 —— 每个任务一间独立房间，用完即拆；对想把 Agent 部署进公司内网的企业，它提供了策略自定义、多租户隔离和全程审计；对金融、政务这类安全敏感场景，微虚机沙箱可以提供硬件级隔离这道最硬的墙。
One Platform, Super Teams。让 AI 从一个助手进化为一支团队之后，openJiuwen 又用 JiuwenBox 给这支团队配上了安全沙箱，让团队再稳稳干活，让用户放心放手。
相关资源：
JiuwenBox AtomGit：https://atomgit.com/openJiuwen/jiuwenswarm/tree/develop/jiuwenbox
JiuwenBox GitHub：https://github.com/openJiuwen-ai/jiuwenswarm/tree/develop/jiuwenbox
WorkSwarm 在线体验，领海量免费 Token： https://openjiuwen.com
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
