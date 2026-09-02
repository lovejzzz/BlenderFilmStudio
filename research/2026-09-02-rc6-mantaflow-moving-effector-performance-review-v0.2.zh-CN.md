# RC6 Mantaflow moving-effector / performance review v0.2

日期：2026-09-02

范围：只读一手资料调研；不修改 attempt-56 的冻结参数或阈值。

## 结论

此前 Final-192 前十帧约 32 分钟并不指向 M2 Max 故障。项目本机已有
resolution-192、7 帧 Data+Mesh 约 1,454 秒的基线，即约 208 秒/帧；
32 分钟/10 帧约 192 秒/帧，处于同一量级。旧问题是 pipeline 太早把
Final 档用于参数搜索，而不是渲染或机器异常。attempt-56 的 24 帧
Preview-96 Data+Mesh 实测 280.74 秒，证明分层后已经回到分钟级。

## 一手资料与可复用产品规则

1. Blender 把移动碰撞体作为 Fluid Effector；`subframes` 用于帧间额外
   采样，减少快速障碍留下的碰撞空隙。软件应从 Bullet 实测最大表面
   位移与当前 voxel 尺寸推导候选 subframes，再用穿透、体积与 containment
   联合验收，不能使用跨项目固定魔数。
   [Blender 5.2 Effector manual](https://docs.blender.org/manual/en/5.2/physics/fluid/type/effector.html)
   [FluidEffectorSettings API](https://docs.blender.org/api/5.2/bpy.types.FluidEffectorSettings.html)

2. `surface_distance` 以网格单位扩大障碍区域，同时会压缩容器有效空间。
   封闭杯体必须使用度量一致、闭合、尽量简洁的 collision effector；渲染
   细分不应进入 moving-effector 求解网格。
   [Blender 5.2 Fluid cache manual](https://docs.blender.org/manual/en/5.2/physics/fluid/type/domain/cache.html)

3. APIC 适合作为慢速杯内连续流动候选；FLIP 更倾向分散飞溅。选择应由
   镜头/物理目标和测量结果决定，不能声称 APIC 普遍更真实。
   [Blender 5.2 Domain settings](https://docs.blender.org/manual/en/5.2/physics/fluid/type/domain/settings.html)
   [APIC original paper](https://www.math.ucla.edu/~cffjiang/research/apic/paper.pdf)

4. `particle_radius` 属于模拟守恒控制；`mesh_particle_radius` 属于表面
   重建控制。物理快照变化使 Data+Mesh 失效，表面快照变化只使 Mesh
   失效，材质/灯光/相机变化不应使任一缓存失效。禁止用更厚的 Mesh
   掩盖真实粒子损失。
   [FluidDomainSettings API](https://docs.blender.org/api/5.2/bpy.types.FluidDomainSettings.html)
   [Liquid Mesh manual](https://docs.blender.org/manual/en/5.2/physics/fluid/type/domain/liquid/mesh.html)

5. Modular cache 的 Data 与 Mesh 是独立阶段。每次运行必须核对真实
   config/Data/Mesh 文件区间，而不是只相信 UI Frame End；高分辨率时
   Resumable 会增加存储成本。
   [Blender 5.2 Fluid cache manual](https://docs.blender.org/manual/en/5.2/physics/fluid/type/domain/cache.html)

6. Resolution Divisions 作用于 domain 最长边。当前 0.90 m 最长边从 96
   升到 192，基础体素数约从 31.5 万增至 255 万，即约八倍，而压力求解、
   粒子、Mesh 与 I/O 的实际倍率可能更大。产品 UI 必须同时显示 tier、
   domain、resolution、voxel、subframes、Data/Mesh/Render 分项耗时、缓存
   字节、swap 与热状态，不能只显示一个“每帧耗时”。

## 对下一步的约束

attempt-56 已证明 containment/topology 可以通过而体积仍失败。下一步先
在相同 physics snapshot 上观测完整 FLIP 粒子 roster，区分 Data 层损失与
Mesh 重建损失；在诊断前不改 simulation radius、mesh radius、阈值，也不
进入 Final、real impact 或渲染。
