# PC5 C3：显式 World 与宿主原生物理发射

Attempt-03 在 empty factory scene 的 null World 上停止，reopen/render/physics 均为零。随后只读宿主 API 探针确认两点：第一，empty factory scene 必须显式创建 World；第二，此 Film Studio Engine 的 `RigidBodyObject` 不公开 `linear_velocity` / `angular_velocity` 写接口，但公开可动画的 `kinematic`。

C3 显式创建摄影棚 World。球的初始速度改用 Blender 官方刚体工作流表达：球先作为 kinematic active rigid body 在冻结的短发射段内做线性位移/旋转，在第 27 帧切为 dynamic，此后直到第 120 帧没有位置或旋转关键帧，所有碰撞、反弹、滚动、瓶子倾倒和静止都由 Bullet 求解。三个瓶子从始至终没有动画关键帧。审计只允许发射帧之前的球初始条件 keyframes，继续禁止任何目标或最终姿态 keyframe。

这不是“摆倒”：关键帧只定义碰撞前的发射装置，等价于给球初速度；结果姿态完全未知且由内置物理引擎求得。模型、质量、摩擦、阻尼、三镜头、60° 三瓶倾倒、重开复算和资源门槛保持不变。Attempt-04 使用 fresh roots。
