# PC7：碰撞传播和非摆拍结果通过，照片级电影真实感仍未通过

PC7 关闭了 PC6 最明显的两个问题，而且没有用最终姿态关键帧换取好看的画面。

第一，软件不再把“第一个物体刚有响应”误当成最佳撞击镜头。它逐帧读取五个目标的
evaluated world tilt，先最大化同时运动的目标数，再最大化合计角度步长，最后才用最早
帧打破平局。正式运行选择 frame 38：五个目标同时 active，合计角度步长
`30.55164633°`。24 帧短片从 frame 32 连续走到 frame 55，直接检查可见倾倒波沿整排
传播，不存在从接触画面跳到摆好的结果。

第二，软件只在求解前加入由 SceneSpec hash、seed、目标序号和 channel 派生的受控
微差：位置、yaw、摩擦和回弹。它不能写目标最终条件。Blender/Bullet 最终得到五个
目标在 28/29/29/30/31 帧响应，终局倾角为 90.00°/90.00°/62.69°/62.32°/90.00°；
frame 86 是独立规则找到的首个八帧稳定窗口。结果中出现相互支撑、悬搭和散落，而非
PC6 近乎整齐的水平终局。

正式证据：

- 产品源码 `c7eece67bff64cbff2de4c6e1aee3248afbca600`，相对已发布 PC6
  基线仅修改 `scripts/modules/film_studio_causal.py`，116 additions / 15 deletions。
- 一次 clean native arm64 build；binary SHA-256
  `b1d80c33d0f79579958667369a0bc09b368e453092d72e1680d3bfe11ff99580`。
- 12 个 authority negative controls，三次产品启动，一次合法场景 mutation，三张
  960×540 still，24 张 clip frame，一次 save/reopen。
- 目标 pose keyframes=0；actor release 后 pose keyframes=0；五个最终倾角重开差全部
  0.0°；motion selection exact。
- 独立审计 `27/27 PASS`，audit self
  `917899768f5fcf39b57f1c6e5af2ad5f21bbc259b15aad03475b92eacacaee38`。
- 直接视觉复核 self
  `c1654213b29eeec82c022358cd91f25e496a875b954642278e15ae0e48d09744`；
  acceptance self
  `39ebb081600694e15e11331eaad683e85d6fc63d192d46d58994b68a6ef61b8f`。

视觉判决是
`PASS_PHYSICAL_PROPAGATION_AND_UNSTAGED_AFTERMATH_NOT_PHOTOREAL_FILM_QUALITY`。
这比 PC6 明显进步：冲击帧从 first-response 28 移到 propagated-motion peak 38，
impact 同时 active 的目标达到五个，证据从三张 still 扩展到绑定的连续短片，终局也
不再近乎一致水平。最终位姿权限没有变化，仍完全属于求解器。

诚实边界也很清楚：现在动作可信，但仍像精致的风格化物理演示。球缺少快门可见的
运动模糊和接触压缩；目标与地面缺少更细的接触响应；没有受限的二次物理、环境细节、
磨损和声音。下一门 PC8 只能在保留本次 primary Bullet solve 的前提下增加快门、接触
与二次物理真实感，不能用尘土、碎片、摇镜或材质掩盖主碰撞，更不能手工修最终姿态。
