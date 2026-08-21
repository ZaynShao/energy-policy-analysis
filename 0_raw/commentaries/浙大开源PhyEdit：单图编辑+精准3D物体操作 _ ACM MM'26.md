---
title: 浙大开源PhyEdit：单图编辑+精准3D物体操作 | ACM MM'26
source_account: 新智元
source_url: https://mp.weixin.qq.com/s/kAQk_Zi-h0jdU3kPp7WvKQ
date_published: '2026-08-18'
fetched_at: '2026-08-20T07:32:36+08:00'
source: wewe-rss
---

# 浙大开源PhyEdit：单图编辑+精准3D物体操作 | ACM MM'26

新智元报道
图像生成模型正从「会创作」转向「可操作」。
但把图片里的物体真正搬到另一个三维位置，仍是一件比换颜色、改风格困难得多的事。
浙江大学ReLER团队最新开源的PhyEdit，展示了一种新的组合方式：用现成3D foundation model明确目标几何，再让强大的DiT图像编辑器负责最终渲染。
结果是，单张图片里的物体不但能从近处移到远处、穿过遮挡区域，还能沿用户指定的三维轨迹形成连续状态。
在ManipEval benchmark上，PhyEdit的DIoU达到65.33、Chamfer降至18.93。与Nano Banana Pro相比，前者高出5.36，后者降低6.40；匿名盲测中，PhyEdit获得78.0%的整体偏好率。
该工作已被ACM MM 2026接收。
论文：https://arxiv.org/abs/2604.07230
项目：https://nenhang.github.io/PhyEdit
代码：https://github.com/nenhang/PhyEdit
模型权重：https://huggingface.co/ruihangxu/PhyEdit
RealManip-40K：https://huggingface.co/datasets/ruihangxu/RealManip-40K
下面的机械臂没有出现在训练数据中。用户给出一条弯曲轨迹后，PhyEdit在不同目标点生成关键状态，再由视频模型补齐中间画面。
实线边框对应PhyEdit直接生成的帧，虚线边框对应插值帧。移动过程中，机械臂、红笔、桌面和纸张之间的尺度与位置关系保持稳定。
这不是一个自主预测动作的dynamics model：轨迹仍由用户提供。PhyEdit做的是另一件更明确的事——把给定三维动作渲染成可信的视觉状态。
现有模型经常能理解「移动哪个物体」，却无法判断它在目标位置应该多大、位于谁的前后。典型失败包括源位置残留、深度错误、只完成多个目标中的一部分。而PhyEdit在处理物体遮挡、深度方向大幅变动和多物体操作时更加稳定。
ManipEval不只比较二维box，还包含深度误差、点云Chamfer、质心距离、relocation-aware DINO和物理合理性等指标。PhyEdit的Phys-VLM达到93.72，同时DeQA与其基础模型Qwen-Image-Edit几乎持平，说明几何提升没有明显换来画质退化。
PhyEdit默认使用Depth-Anything-3，但框架并未把编辑器和某个几何模型绑死。研究者固定同一个editor checkpoint，只替换负责构建preview的3D backbone。
DA2、MoGe、VGGT、Pi3X和DA3相对Nano Banana Pro都保持正向平均几何增益，其中DA3的Geo.Δ为+5.55，Pi3X为+3.94，MoGe为+3.62。
这意味着更好的几何估计器可以继续抬高上限，但PhyEdit的收益并非某个特定depth model的偶然产物。在3D preview出现问题时，PhyEdit仍能通过backbone的先验，利用原图和指令的信息，生成较为合理的结果。
加入3D控制后，模型原有的普通编辑能力是否会消失？团队用300条额外指令测试颜色、材质、图案和局部元素。
PhyEdit必须在同一次生成中同时完成三维移动和附加编辑，综合成功率为87.5%。Qwen-Image-Edit在单独editing-only运行中为88.8%，差距只有1.3个百分点；但PhyEdit的三维Chamfer为20.97，远低于Qwen-Image-Edit的46.31。
PhyEdit使用Qwen-Image-Edit作为生成backbone。用户选择目标物体并给出三维位移后，冻结的3D model估计深度和相机参数，把masked pixels反投影成点云，在三维空间中移动，再投影为preview。
这张preview可能很粗糙，却能消除语言中的空间歧义。它明确给出物体的新位置、投影尺度和前后顺序；原图继续提供纹理、身份和环境，DiT则负责将两者融合为自然画面。
因此，PhyEdit不是把点云渲染直接当作结果，而是把它变成生成模型能消费的「3D草稿」。
为了避免最终图像只在外观上相似、深度仍然错误，训练还加入pixel-level SILog depth loss。与latent-to-latent、latent-to-depth方案相比，直接监督解码后图像的深度取得最佳几何指标。
团队构建了RealManip-40K，包含41,154对真实源图和目标图，提供深度、mask和代表性三维坐标，覆盖远近变化、遮挡切换和多物体操作。
数据管线会利用3D模型的camera token聚类筛选近静态机位，避免把相机移动误当成物体位移；之后再完成检测、跟踪、分割、深度重建和VLM过滤。
开源仓库提供了完整GUI。用户可以上传图片、选择多个物体，在点云中调节平移与旋转，先查看实时几何preview，再调用模型生成最终图像。
PhyEdit对「physically-grounded」的定义并非完全的物理仿真：显式模块处理刚体位移、投影、尺度和深度顺序，不计算力、碰撞或动力学。透明反光物体、极端近景移动以及严重的深度和分割错误仍是失败来源。
但这项工作的意义也正在于边界清晰：当基础生成模型已经很会「画」，就可以把空间中可计算、可验证的部分交给几何模块，而不是继续期待一个纯文本prompt自动解决所有三维歧义。
论文由浙江大学ReLER团队完成。第一作者为浙江大学计算机科学与技术学院本科生许瑞航。ReLER团队长期致力于人工智能领域的前沿研究，包括但不限于生成模型、多模态学习、AI+X等方向。
参考资料：
https://arxiv.org/abs/2604.07230
编辑：LRST
