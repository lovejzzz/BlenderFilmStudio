# B62：BlenderFilmStudio 终局电影样片目标冻结

Date: 2026-08-29

Status: **terminal goal freeze — not yet a formal experiment preregistration**

## 停止继续扩张研究目录的条件

BlenderFilmStudio 的下一目标不是再证明一个孤立 API，而是交付一段可以完整观看、可以从零复跑、可以在中断后恢复、并且不依赖生成式视频模型的 Blender 原生成片。达到本文件的全部验收条件后，停止为邻近问题继续创建研究 ID，发布最终边界报告。

## 成片命题

片名：**《守夜人点亮观测核心》**

一个原创机械守夜人进入废弃轨道观测站，靠近控制台，用手触发沉睡的观测核心。环境从冷暗状态切换为暖色核心光；最后一个特写在角色面罩上显示核心反射与视线变化。

选择机械角色而非写实真人是第一支终局管线证明的显式边界：它允许我们认真测试固定资产身份、绑定、接触、材质、反射、灯光状态变化、摄影和运动连续性，同时不把尚未解决的真人皮肤、毛发、口腔与微表演伪装成已完成。

## 冻结结构

- 总长：12 秒，24 fps，288 个交付帧；不允许用插帧或生成式视频补帧。
- 分辨率：1920×1080；scene-linear multilayer half-float ZIP OpenEXR 为母版，另生成可播放交付视频。
- 镜头 1 / `WIDE_APPROACH` / frames 1–96：35 mm 缓慢推进；守夜人从暗部走向控制台，建立角色、空间和主光方向。
- 镜头 2 / `MEDIUM_CONTACT` / frames 97–192：65 mm 小幅环绕；右手与控制台发生明确接触，核心由冷暗转为暖亮，角色与环境共享同一状态变化。
- 镜头 3 / `CLOSE_REFLECTION` / frames 193–288：100 mm 缓慢推近；面罩、眼位和核心反射成为视觉中心，维持上一镜头的角色姿态、核心状态与光向连续性。
- 角色：单一版本的原创机械守夜人；固定 mesh、rig、material、scale、handedness 与 asset hash。
- 环境：单一版本的观测站控制室；固定空间尺度、控制台、核心、world、look rig 与 asset hash。
- 视觉方向：stylized realism；冷青环境光与暖金核心光，受控体积雾、景深、运动模糊、金属与玻璃反射。不得使用后期生成式重绘来隐藏几何、接触或一致性错误。

## 工程验收

1. 从 clean output root 执行一个入口，依次完成冻结 shot brief → SceneSpec → immutable BuildPlan → Blender compilation → render → review/master delivery。
2. 三镜头必须共享同一个角色、环境、核心状态机和 look manifest；只允许明确声明的相机、动作时间与可见性差异。
3. 在第一个镜头完成并拥有 verified receipts 后，受控终止 orchestrator 与 Blender/Codex 工作回合；重新运行同一个入口时必须只从 receipt-derived state 恢复，不重编译或重渲染已完成 immutable stage。
4. 每一个 stage、native process、frame roster、EXR、review proxy、delivery video、资源用量和失败路径均有自哈希 receipt，并可由不导入生产 runner 的 auditor 独立重放。
5. 全序列无缺帧、重复帧替代、空帧、方向翻转、非有限像素或未绑定输出；交付视频必须为 288 帧、24 fps、12 秒，镜头边界 exact。
6. 记录真实 wall time、render time、peak RSS、EXR/PNG/video bytes、磁盘峰值与机械成本；保持至少 100 GiB reserve 加 projected writes。
7. 正式图像管线为 0 generative-video calls、0 neural frame replacement。Codex 可以编排和生成受限结构化数据，但不能直接向成片写像素。

## 电影质量验收

自动审计只负责证明结构、过程和文件，不得替代审美判断。正式结束前必须产生一个匿名审片包，由人类针对以下维度逐镜打分并留下原始 response：

- 角色身份与比例跨镜头一致；
- 控制台接触无漂浮、穿插或时间错位；
- 冷→暖灯光变化具有明确因果且跨切点连续；
- 摄影景别、构图、焦点和运动服务同一叙事 beat；
- 动画重量、停顿与反应可读；
- 材质、反射、体积和色彩达到可接受的 stylized-cinematic 完成度；
- 三镜头作为一段成片观看，而不是三张独立技术图。

人类审片未完成或未通过时，只能发布“工程管线完成 / 电影质量待审或未通过”，不能发布“影院级成片完成”。

## 必须先做的 Phase 0

本文件只冻结终局目标，不授权正式 288 帧渲染。下一步先完成有界 Phase 0：建立原创角色与环境的 asset manifest、三镜头 animatic、接触与灯光状态机，以及少量真实 Cycles 校准帧；根据校准在正式 B62 协议前冻结 samples、timeout、projected bytes 与最大允许重试。任何失败必须留下证据并触发新的 correction，而不是改写本目标。

## 声明边界

即使 B62 通过，也只证明这一个 stylized-realism 机械角色短场景的端到端 Blender 原生生产能力。它不证明写实真人、任意剧本、长片规模、跨硬件像素确定性、零人工美术劳动或“订阅之外零成本”。
