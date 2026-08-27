# B52-D10 · Blender multipart temporal adapter fresh holdout 协议

日期：2026-08-27

Spec SHA-256：`147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566`

## 研究问题

D9.1 支持 canonical previous/current RGBA、Depth、owner ID 与 integer motion 上的外部 temporal accumulation，但 production Blender EXR 尚未接入。D10 问一个更窄的接口问题：冻结的 adapter 能否从真实 Blender 5.2 multipart EXR 中重复提取正确通道，并把 Blender 的 previous-screen Vector 转成 D9.1 的 top-left raster motion 约定。

这不是对开发输出的复测。正式夹具使用从未渲染的 173×97、ortho scale 17.3、pass index 101/202/303/404/505，以及新的物体/相机三帧轨迹。development 的 192×108 EXR、坐标和 pass index 都禁止进入正式输入。

## 独立解析 oracle

相机固定零旋转，landscape orthographic 投影的每世界单位像素数冻结为 `173/17.3 = 10`。正式 analyzer 只能用 Python standard-library math：

`screenUp = [w/2 + (objectX-cameraX)*w/orthoScale, h/2 + (objectY-cameraY)*w/orthoScale]`

`topLeft = [screenUpX, h-screenUpY]`

`depth = cameraZ-objectZ`

它不得导入 `bpy`、`bpy_extras`、`mathutils`，不得读取 Blender source report 中的投影坐标，也不得复用 development observation 的坐标。

物体夹具冻结 `Vector.XY=(-7,+3)`、`Vector.ZW=(-11,+5)`；相机夹具冻结 `(+6,-4)` 与 `(+13,-8)`。static 为零。D9.1 motion 转换固定为 `(-X,-Y)`，分别得到 `(7,-3)`、`(-6,+4)` 与 `(0,0)`。

## Source、ownership 与 orientation

每个 fixture/repeat/frame 都由一个全新的 Blender process 从 factory state 构建；previous frame 0 与 current frame 1 不共享进程。三 fixture × 两 repeat × 两 frame 共 12 个 Cycles CPU 进程、12 次 render。所有 keyframe、material、camera、render state、pass state 与 layered Action 结构必须写入并复查 source report。

唯一允许的 subimage roster 是：

1. `BFS_MASTER.Combined` RGBA；
2. `BFS_MASTER.Depth` Z；
3. `BFS_MASTER.Vector` XYZW；
4. `BFS_MASTER.Object Index` X。

旧内部名 `IndexOB` 不得被静默接受。每帧五个 declared owner 都必须可见，3×3 analytic probe 必须全为各自 ID。Depth 必须在这些 owner pixels 上命中 9.5/8.25/6.75/7.75/7.5，最大误差不超过 `1e-6`。顶部与底部 marker 的 top-left centroid 顺序用来否决 vertical flip。

## Vector 门与反例约束

Moving owner 上正确 pair 的 endpoint error 必须满足 p99 ≤`1/4096 px`、maximum ≤`1/1024 px`。最近的错误 pair/sign/component 候选 median error 必须 ≥4 px，保证任务具有判别力。

Static pair 只要求 p99 ≤`1/4096 px`、maximum ≤`1/1024 px`，不要求逐位零。这个容差显式继承 D5 的 retained counterexample：D5 static Cycles Vector 曾达到 `2.6702880859375e-5`，不能因本次 development static 恰好为零而删除。

## Canonical adapter 与正式进程矩阵

每个 fixture/repeat 的 adapter 读取 previous/current 两个 multipart EXR，写出七份 top-left little-endian float32 raw：previous/current RGBA、previous/current Depth、previous/current Object Index，以及 `motion=(-current Vector.X,-current Vector.Y)`。如果 output directory 或 report 已存在必须拒绝覆盖。

六个 fresh Python adapter process 后，一个独立 analyzer 重新打开全部 12 个 EXR，不导入 adapter 实现，重建七份 arrays 并要求 byte exact。两次 source decoded passes 与两次 canonical arrays 都必须 exact。

正式矩阵固定为 12 Blender + 6 adapter + 1 analyzer = 19 个唯一 child PID、12 次 Cycles ray render、0 source `.blend` 和 0 external asset。每 fixture 固定输出 Combined、Depth、ownership 和 previous-motion magnitude 四张 PNG 与 sidecar，共 12+12；diagnostic 不参与 measurement。

## 判定与下一边界

34 个 attacks 覆盖 parents、D5 counterexample、development identity、freshness、runtime/disk/tool freeze、scene/action/render、process/PID、multipart roster/channels、repeat、独立 oracle、两组 Vector、component/sign、D9 坐标、static tolerance、Depth、ownership、orientation、adapter arrays、diagnostics、operation boundary 与 self-hash。

任何一门失败，结论必须是 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED`，并保留 counterexample；不得把 Blender production passes 接入 D9.1。全部通过才允许 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_SUPPORTED`，且只允许下一步另行预注册真实 textured render → adapter → D9.1 accumulator → Raw EXR bridge 的 opaque integer-motion end-to-end holdout。

D10 不主张 perspective、subpixel、deformation、transparency、multi-owner、Cryptomatte、hair、volumetric、DOF、motion blur、跨引擎/平台复现、temporal 画质或电影感。

Formal output root：`experiments/blender-multipart-temporal-adapter-holdout-v0-1/`；预注册时不存在。正式 renderer、adapter、analyzer、runner、audit 与 tests 均尚未实现。
