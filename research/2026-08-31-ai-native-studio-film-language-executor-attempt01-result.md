# PC4-VX2 attempt-01：软件学到了关系，但视觉审核发现机器误判

v0.2 executor 的局部进步真实可见：广角黑柱不再切断人物，中景从同尺度方块堆恢复为可读人物与接触动作；稀疏 panel 与 concentric joint 也比 v0.1 的浮动矩形更接近统一 form language。

本次仍不能接受。广角的 world-bbox overlap 把 atmosphere、floor 与 observation aperture 一并隐藏，破坏环境层；中景 occupancy 为 `0.35712820`，低于计划下限 `0.48`，但 executor 与 27/27 audit 都只检查上限，形成机器 false positive；近景仍由侧面圆形 pod 主导，数据中的四个 facial zones 没有在目标镜头中形成可见层级。

因此结论不是“关系约束无效”，而是软件的下一课必须更严格：先把主体 recenter，再双向验证 occupancy interval；occlusion 需要 pixel-visible mask/depth 或更强的 story-layer semantic，不能用整个 world bbox 代替真实像素；face hierarchy 必须验证目标视角可见性、朝向与表演功能。Attempt-01 全部保留，不回写机器证据。
