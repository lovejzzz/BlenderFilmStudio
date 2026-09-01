# PC5-G1：未见过的形状与数量泛化

PC5 attempt-05 已证明一个受控球撞三瓶场景能够同时通过真实 Bullet 因果、reopen 复算、动态取景和直接视觉审核，但一个作品仍可能只是被脚本记住。PC5-G1 在重构执行器之前冻结新题，防止看过结果后为它写坐标答案。

新题保留 `dynamic_actor → target_group → SETUP / IMPACT / AFTERMATH` 语义，但目标从三个旋转剖面瓶子换成四个带倒角、面板和边带的木质多米诺块；数量、形状、碰撞体、质量、材质和初始布局均由 `CausalSceneSpec` 提供。执行器必须从 spec 读取 cardinality、factory、rigid-body parameters、launch、acceptance 与 shot intent。它可以调用冻结 allowlist 中的程序化资产工厂，不得运行 spec-originated Python、shell、network 或任意 filesystem 指令。

相机只能读取每个 review frame 的 evaluated semantic world bounds、shot direction class、lens 和 occupancy target；不得读取 attempt-05 的瓶子 final coordinates，也不得在代码中出现四块木块的最终坐标。球在 frame 27 后没有 pose keyframe，四个目标从始至终没有 pose keyframe；所有倾倒和最终分布必须由 Blender/Bullet 产生。

机器 PASS 要求四块目标全部最终倾斜至少 55°，第一次响应在 20–72 帧，球在响应前前进至少 2m，reopen 的响应帧完全相同、最终倾角误差不超过 0.01°，三镜头 occupancy/margin 通过，零外部资产/网络/engine mutation。直接视觉审核继续独立回答模型层级、因果可读性、四块目标前后可辨性、阴影重量、材质曝光和三镜头功能；机器不能替视觉代答。

唯一 fresh roots 为 `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC5-G1-2026-09-01-attempt-01` 与 `experiments/causal-studio-generalization/PC5-G1-2026-09-01-attempt-01`。资源、进程与发布边界不超过已接受 PC5：最多 3 次 Blender start、6 次单帧 render、3 张保留 PNG、512 MiB work、64 MiB evidence、零 film-engine 修改或 remote write。

只有当这个冻结新题通过，才能声称软件学到了一个可迁移的基础因果电影模式；即使通过，也只允许返回 PC4 机器人做 capstone，不得声称通用自主电影能力。
