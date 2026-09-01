# RC6 Mantaflow 与电影化桌面物理场景实践调研 v0.1

日期：2026-09-01  
状态：外部一手资料调研完成；本地 RC6 仍在验证，不构成产品接受结论。

## 目的

把“球撞倒装水杯”从一次手工场景改造成 Film Studio Engine 可复用的物理与审片规则：结果由 Bullet 与 Mantaflow 产生，软件自动拒绝体积丢失、碎片化、穿透和扁平灯光，而不是只确认缓存或 PNG 存在。

## 一手资料

- Blender Fluid Effector 手册：<https://docs.blender.org/manual/en/latest/physics/fluid/type/effector.html>
- Blender Fluid Domain Settings 手册：<https://docs.blender.org/manual/en/latest/physics/fluid/type/domain/settings.html>
- Blender Liquid Mesh 手册：<https://docs.blender.org/manual/en/latest/physics/fluid/type/domain/liquid/mesh.html>
- Blender Liquid Diffusion 手册：<https://docs.blender.org/manual/en/latest/physics/fluid/type/domain/liquid/diffusion.html>
- Blender `FluidEffectorSettings` API：<https://docs.blender.org/api/main/bpy.types.FluidEffectorSettings.html>
- Blender `FluidDomainSettings` API：<https://docs.blender.org/api/main/bpy.types.FluidDomainSettings.html>
- Blender BMesh API：<https://docs.blender.org/api/5.1/bmesh.types.html>
- Blender BVH API：<https://docs.blender.org/api/main/mathutils.bvhtree.html>
- APIC 论文：<https://www.math.ucla.edu/~cffjiang/research/apic/paper.pdf>
- Narrow Band FLIP 论文：<https://pub.ista.ac.at/group_wojtan/projects/2016_Ferstl_NBFLIP/nbflip.pdf>
- Blender Studio Lighting 流程：<https://studio.blender.org/tools/pipeline-overview/shot-production/lighting>
- ARRI Lighting Handbook：<https://www.arri.com/resource/blob/83996/409091c612f371b0c68b41d9dcb636db/arri-lighting-handbook-english-data.pdf>
- Blender Light Objects 手册：<https://docs.blender.org/manual/en/latest/render/lights/light_object.html>
- Blender Color Management 手册：<https://docs.blender.org/manual/en/latest/render/color_management/displays_views.html>
- Blender Render Passes 手册：<https://docs.blender.org/manual/en/latest/render/layers/passes.html>
- Blender Camera 手册：<https://docs.blender.org/manual/en/latest/render/cameras.html>

## 官方事实与论文结论

1. Effector `subframes` 用于给快速移动碰撞体增加帧间采样，减少碰撞空隙。
2. 较低 CFL 会在高速流动时增加求解步数；降低 CFL 时必须允许更高的 `timesteps_max`。
3. Fractional Obstacles 能改善倾斜障碍的阶梯边界。
4. `particle_radius` 影响底层液体体积：丢体积时可增加，涨体积时应减少；`mesh_particle_radius` 只改变表面重建粒子的大小，不能证明底层体积正确。
5. APIC 的目标是比纯 FLIP 更稳定，同时保留运动活力。Narrow-band FLIP 不保证自由表面处的精确质量守恒，因此必须测量，不能假设。
6. 水的运动黏度约为 `1.002e-6 m²/s`；不能为了让画面稳定而把水改成蜂蜜。
7. Blender Studio 的灯光工作可拆成 key、key-soft、fill 与 rim；ARRI 把 fill 定义为大而柔、只抬暗部而不制造第二组反向阴影的光。

## 本地测量与纠正

RC6 F6 attempt-10 的 48 帧直接审片正确拒绝了碎片状液体，但该审片记录中的 `domainLargestDimensionMeters=2.1` 是诊断笔误。冻结场景实际使用中心 `(0.45, 0, 0.45)`、scale `(1.25, 0.8, 0.45)` 且已应用缩放，因此 domain 尺寸为 `2.5 × 1.6 × 0.9 m`。历史证据不原位修改；本记录做版本化纠正。视觉拒绝结论不受影响。

以 F7 `resolution_max=192` 计算，基础体素边长约为：

`h = 2.5 / 192 = 0.0130208333 m`

使用 attempt-10 的 Bullet 轨迹，杯子表面在撞击段的逐帧保守位移为：

`surfaceDisplacement = translation + cupRadius × angularDelta`

实测峰值约 `0.1018–0.1351 m/frame`。若要求每次 effector 采样的表面位移不超过 `0.5h`，则需要约 `15–20` 个 subframes；F7 冻结值 `4` 明显偏低。这个半体素规则是基于官方 subframe/CFL 定义的工程推断，不是 Blender 官方阈值。

## 软件应采用的物理校准顺序

1. 先跑静止容器对照，测量求解器自然体积漂移。
2. 再跑慢速倾倒对照，验证碰撞体闭合、壁厚、fractional obstacle 和局部空间 containment。
3. 最后跑真实 Bullet 撞击；不得跳过前两组后直接用表面半径“糊住”碎片。
4. effector subframes 应由冻结的 Bullet 轨迹与体素尺寸计算，而不是写死：

   `ceil(max(translation, radius × rotation) / (0.5h)) - 1`

   实现时可采用更保守的 `translation + radius × rotation`，并受资源上限约束。
5. 首轮时间设置采用 `use_adaptive_timesteps=true`、`CFL=1.0`、`timesteps_min=2`、`timesteps_max=12–16`；若仍穿透，可在新合同中测试 `CFL=0.5`。
6. `particle_radius` 从 `1.0 / 1.1 / 1.2 / 1.3` 做小步冻结矩阵，以体积漂移最小者为准；不能一次跳大并从好看的单帧倒推参数。
7. `mesh_scale=2` 与 `mesh_particle_radius=2.0` 先保持默认。只有底层体积和连通性通过后，才允许小幅调整表面重建。
8. domain 在整个动作范围保留至少约 8–12 个体素余量；任何触边或 outflow 都必须单独记录。

## 软件应自动拒绝的液体结果

以下是待对照组校准的首版工程门槛，不冒充官方阈值：

- 评估网格必须闭合且 manifold，否则体积指标无效并直接拒绝。
- 体积相对静止对照中位数保持在 `[0.95, 1.05]`；相邻帧跳变不超过 3%。实际容差取 `max(5%, 3 × 静止对照漂移)`。
- 最大连通体积占比不低于 90%；大于总量 1% 的额外连通块不超过两个，微小飞滴另计。
- 碰撞前容器外液体体积占比小于 0.5%；液体与 effector 交叠体积小于 1%。
- 容器局部空间中的液体质心必须留在内腔包围体；速度或加速度尖峰超过邻域中位数三倍时拒绝。
- PNG 审片仍是必要的最终保护，不能用几何指标替代。

当前 F7 的 40% 体积保持与 50% 最大连通分量只是识别严重失败的宽松可行性门槛；它不能成为产品质量阈值。

## 灯光与镜头的下一阶段门槛

当前 RC6 画面过平：墙面与桌面值域接近、主光过宽、暗部没有塑形、主体缺少轮廓分离。物理通过后应单独冻结灯光迭代，避免与模拟参数混淆。

- Key：桌面侧前方约 35–55°、高度约 30–45°的大 Area Light，必须让球、杯体和液面出现明确明暗面。
- Fill：靠近镜头轴的大软光，从 key 的 18–35% 起步，只抬暗部。
- Rim：后侧掠过杯口、球缘和液面，只做前景/主体/背景分离。
- 背景比动作平面低约 1–2 stops；优先降低 world 或使用遮光，而不是负功率灯。
- 使用 AgX 保护高光；接触点附近不得剪白。
- 因果动作段保持固定机位或极小跟随，不在接触帧切镜头；接近、接触、结果必须在同一镜头中可读。

待校准的自动画面指标：接触点无遮挡率、关键物体投影面积、接触区高光剪切、shadow/key 中位亮度比、rim 在主体 mask 中的占比，以及前景/主体/背景的亮度分离。所有数值必须先用当前场景 A/B 对照冻结，不能看完结果后放宽。

## 当前结论

RC6 的 Bullet 因果链已稳定证明“不是摆放”；液体仍未证明真实感。下一步不是继续手调某个作品，而是把时空采样、体积守恒、连通性和灯光层次变成 Film Studio Engine 的通用编译与验收规则。
