# PC8 预注册：从真实物理速度计算快门，而不是给画面涂模糊

PC7 已经证明五个目标的倾倒传播和最终落点来自 Blender/Bullet，问题转为如何把同一条
真实运动拍得更像电影。PC8 只解决一个可证伪的问题：软件能否从画面中的 evaluated
物体速度计算快门，让运动方向产生可见模糊，同时保持物体数量、面板、黑色横带和碰撞
方向可读。

正式运行前披露的开发 A/B 使用 PC7 accepted `.blend`，没有修改源码或正式 root。
frame 37→38 的球与五个目标原点位移约为 16.25–21.46 px/frame。0.5-frame shutter
产生了真实 Blender transform blur，但视觉上过重；以 6 px 为目标的约 0.3-frame
shutter 保留了速度与细节。这个观察只用于冻结阈值，不是正式证据。

SceneSpec v0.3 只能声明目标模糊像素、上下限、CENTER shutter position 和参与测量的
semantic roles。产品必须在 motion-selected IMPACT camera 中测量 actor+targets 的
投影位移，取 median，以 `targetBlurPixels / medianPixelsPerFrame` 计算并 clamp shutter。
SceneSpec 不能给出最终 shutter，不能调用 compositor/vector blur，也不能携带 Python、
shell、网络或任意文件权限。

PC7 的主物理结果是不可退化的控制：response 28/29/29/30/31、impact 38、五个 active、
aggregate step `30.55164633°`、aftermath 86、五个 final tilt、全部 initial conditions、
zero target/post-release actor pose keys 和 exact reopen 都必须逐值保持。正式证据必须同时
保留 sharp impact control、产品 blurred impact、三张产品 still 和 24-frame clip，并由
直接视觉复核判断模糊是否真实可见但没有损坏碰撞叙事。

即使通过，PC8 也只证明 measured shutter 是一个通用电影规则，不证明照片级材质、
接触形变、二次物理、声音或复杂角色场景。下一层仍必须由真实物理状态驱动，不能用
尘土、碎片、摇镜或后期效果掩盖主碰撞。
