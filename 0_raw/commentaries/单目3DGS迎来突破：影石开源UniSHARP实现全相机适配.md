---
title: 单目3DGS迎来突破：影石开源UniSHARP实现全相机适配
source_account: 机器之心
source_url: https://mp.weixin.qq.com/s/Avg3VVOJZVbga5H6MZQlCQ
date_published: '2026-06-26'
fetched_at: '2026-07-01T07:32:00+08:00'
source: wewe-rss
---

# 单目3DGS迎来突破：影石开源UniSHARP实现全相机适配

影石研究院发布面向异构成像系统的单目新视角合成模型 UniSHARP（Universal Sharp Monocular View Synthesis）。作为首个统一透视、广角、鱼眼与 360° 全景相机的单目 3DGS 模型，UniSHARP 只需一张输入图像，即可通过单次推理在秒级时间内获得场景的高斯点云，无需多张图像输入或逐场景优化。
该方法不再依赖针孔相机假设，而是以统一的几何表示打通不同相机模型之间的壁垒，通过融合 2D 语义特征与 3D 几何特征来预测 3D 高斯场，并支持混合相机训练与 Pose-Free 免标定推理 —— 真正实现一张图、一个模型、适配所有相机。
团队同步构建含 30 万张全景图及深度的仿真数据集 OmniRooms，并建立覆盖多种相机类型的 FoV 分层 benchmark。目前，训练与测试代码、模型权重、数据集与在线 Demo 已经全部开源。
近年来，3D Gaussian Splatting（3DGS）与新视角合成发展迅速，但绝大多数方法仍默认输入来自普通透视相机，然而真实世界天然存在全景相机、鱼眼镜头、超广角运动相机等异构视觉系统。另外，即便有些方法面向全景图，也常依赖多张图像输入或逐场景优化，但许多实际应用场景往往只能拿到单张图像 —— 一张随手拍的手机或全景相机的抓拍照片，却希望能够立刻获得高质量、可交互的新视角渲染。
针对以上问题，有两条直觉路径：一是把透视模型「微调」到更大视场，但由于模型绑定在针孔相机的归一化设备坐标系上，本质上难以在非针孔成像域中正确预测几何和处理畸变；二是将大图切块、重投影为多张透视视角分别处理，但这又带来额外计算开销，并在拼接处引入明显的接缝伪影与几何不连续。
UniSHARP 正是在这一背景下应运而生，让单目 3DGS 摆脱针孔假设，用一张图、一个模型，覆盖从普通照片到 360° 全景的统一重建。
论文标题：UniSHARP: Universal Sharp Monocular View Synthesis
论文：https://arxiv.org/abs/2606.07514
项目主页：https://insta360-research-team.github.io/Unisharp-website/
代码：https://github.com/Insta360-Research-Team/UniSHARP
数据集 OmniRooms：https://huggingface.co/datasets/Insta360-Research/OmniRooms
在线 Demo：https://huggingface.co/spaces/Insta360-Research/UniSHARP
模型权重：https://huggingface.co/Insta360-Research/Unisharp
Ray-based统一表示：不再依赖针孔相机假设
现有单目 3DGS 方法（如 SHARP、Flash3D）多在窄视场透视数据上训练，几何预测与图像平面坐标强绑定，向鱼眼、全景迁移时泛化困难。UniSHARP 的核心思路是把场景表示搬到 ray-distance 空间。
具体而言，模型为每个像素预测一条单位视线方向和沿射线的径向距离，三维点由二者共同确定。无论输入是透视、鱼眼还是 ERP 全景图，高斯球都在同一度量的三维空间中定义，不再被某种相机模型绑死。这一设计受 UniK3D 的启发，使 UniSHARP 能够原生适配不同视场与畸变，而无需将全景硬切成多张透视图再拼接 —— 对比显示，使用 SHARP 推理全景图的 6 个 cube 时，会出现明显的拼接伪影和几何不一致，而 UniSHARP 可渲染连贯一致的全景目标视图。
几何锚定高斯 + 特征条件残差：稳定几何与细腻外观兼得
在统一射线网格空间中，UniSHARP 先构建双层 Geometry Anchored Gaussians（几何锚定高斯）：第一层对齐可见表面，第二层捕捉遮挡区域与高频结构，为单目重建提供稳定的基础高斯场；再融合 2D 语义特征与 3D 几何特征，预测 Feature Conditioned Gaussian Residuals（特征条件残差），对高斯球进行精细化修正，得到最终可渲染的高斯点云。
相比直接将 RGB 图像与深度图喂入解码器的传统做法，这种设计能更充分地利用几何先验与语义上下文。此外，针对 ERP 全景图的严重畸变，团队引入球面高斯初始化与畸变感知概率 Dropout，在 HM3D 等全景数据上效果尤为显著。
混合相机训练与 Pose-Free 推理：贴近真实落地场景
训练阶段，UniSHARP 在透视（RealEstate10K、DL3DV、WildRGB-D）、鱼眼（ScanNet++ Fisheye）、全景（HM3D、OmniRooms）数据上混合采样、统一架构，不引入相机专用分支 —— 所有样本都转换为同一套射线接口，共享同一网络。
更贴近实际应用的是 Pose-Free 模式：当用户没有标定内参时，模型可从预测射线场自动推断相机类型与渲染几何，无需手动提供透视或鱼眼参数。
OmniRooms 与 FoV 分层 Benchmark：30 万全景图填补数据空白
为系统评估从 60° 到 360° 的新视角合成能力，团队构建了 FoV 分层 benchmark，并发布仿真数据集 OmniRooms：
16 个大型室内场景；
约 30 万张 1024×2048 ERP 全景图及对应深度；
适配 3D 重建，尤其是 3DGS 任务；
每个锚点在 0.5 米体素网格上渲染 1 个中心相机与 29 个局部小位移相机。
基准测评：透视不掉队，全景大幅领先
在透视数据集上，UniSHARP 没有因「做通用」而牺牲窄视场性能：
均全面超越 SHARP、Flash3D 等基线。零样本 Tanks & Temples 上，UniSHARP 同样取得最佳 PSNR。
在全景场景，优势更加明显：
全栈开源：代码、数据、模型、Demo 一键可用
UniSHARP 不止于提出一个新的单目 3DGS 模型，而在于展示了一条面向真实异构成像系统的完整路线：用 ray-based 空间统一不同相机几何，用几何锚定与特征残差稳定预测高斯场，用混合相机训练实现跨视场迁移，用 OmniRooms 与分层 benchmark 支撑可复现评测，并用 Pose-Free 机制降低部署门槛。
对 Insta360 而言，这与全景相机、运动相机的产品场景天然契合 —— 用户拍下的每一张 360° 照片、每一段鱼眼素材，都有机会被快速转化为可漫游的三维空间。对更广泛的社区，统一单目 3D 视觉也为机器人导航、AR/VR 内容创作等应用提供了新工具。
© THE END
转载请联系本公众号获得授权
投稿或寻求报道：liyazhou@jiqizhixin.com
