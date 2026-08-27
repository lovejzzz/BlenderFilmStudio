# B52-D10.1 · Blender multipart temporal adapter float32 fresh holdout 协议

日期：2026-08-27

Spec SHA-256：`11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b`

## 为什么必须是新实验

D10 的正式 verdict 是 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED`，独立 audit 是 `FAIL`。虽然所有 pass payload、adapter 和 repeat measurements 通过，冻结结构 verifier 把 JSON double literal 与 Blender RNA float32 读回值逐值比较，令 `SCENE_STRUCTURE` 和 `ANIMATION_STRUCTURE` 失败。不得修改 D10 analyzer 后重跑同一批 173×97 数据，也不得把 D10 改写为 supported。

D10.1 只修复这一项已定位的测量契约，同时重新承担完整 payload 风险。它使用从未渲染的 181×103、ortho scale 18.1、全新 object names、geometry、IDs 111/222/333/444/555 和全新 object/camera trajectories。D10 EXR、arrays 与 measured coordinates 禁止成为 D10.1 formal inputs。

## typed structural oracle

结构比较不采用 epsilon。spec 明确区分两种字段：

1. 进入 Blender RNA float storage 的 location、rotation、scale、ortho scale 与 FCurve control-point frame/value，期望值先经过 `struct.unpack('<f', struct.pack('<f', float(value)))[0]`，之后与 report exact comparison；
2. name、enum、integer frame、pass index、owner/action roster、layer/strip/channel-bag index、data path、array index、interpolation、render/pass state、process count 与 artifact identity 一律保持 exact，禁止 canonicalize。

三个 sensitivity controls 在正式 analyzer 内独立执行：跳过 18.1 的 binary32 round-trip 必须产生已知不相等；把 canonical ortho scale 向正无穷方向改变一个 finite float32 ULP 必须被 `SCENE_STRUCTURE` 拒绝；把一个 pass index 加一也必须被拒绝。全局 epsilon、十进制位数 rounding 或接受相邻 float32 都违反协议。

## payload oracle 与未见夹具

相机保持零旋转，nominal projection 为 `181/18.1 = 10 px/world unit`。独立 analyzer 只使用 Python standard library 与预注册 JSON 值：

`screenUp = [w/2 + (objectX-cameraX)*w/orthoScale, h/2 + (objectY-cameraY)*w/orthoScale]`

`Vector.XY = previousScreenUp-currentScreenUp`

`Vector.ZW = currentScreenUp-nextScreenUp`

`D9.1 motion = (-Vector.X,-Vector.Y)`

三组夹具冻结为：

- object motion：XY `(-11,+7)`、ZW `(-18,+11)`、D9 motion `(+11,-7)`；
- camera motion：XY `(+9,-6)`、ZW `(+20,-12)`、D9 motion `(-9,+6)`；
- static depth/owner：两组 Vector 都为零。

Moving endpoint gate 与 D10 完全相同：p99 ≤`1/4096 px`、maximum ≤`1/1024 px`，nearest wrong component/sign/pair candidate median ≥4 px。Static 同样保持非零容差，以保留 D5 的 `2.6702880859375e-5` counterexample；不得改成 exact zero。

五个 opaque single-owner depths 是 11.25、10.5、8.75、9.25、9.0，最大误差仍为 `1e-6`。每帧五个 pass index 都必须可见；analytic 3×3 probe 全部 exact；top marker 的 top-left centroid row 必须小于 bottom marker，否决 vertical flip。

## 真实 Blender 与 adapter 矩阵

每个 fixture/repeat/frame 在 factory state 的全新 Blender 5.2.0 LTS process 中生成 opaque emission planes，并用 Cycles CPU、1 sample、fixed 4 threads、无 adaptive sampling、denoising、motion blur 或 persistent data 输出 multipart float32 EXR。正式边界为：

- 3 fixtures × 2 repeats × previous/current = 12 Blender processes、12 Cycles ray renders；
- 6 fresh adapter processes，各写 D9.1 格式的 previous/current RGBA、Depth、Object Index 与 `motion=(-X,-Y)` 七份 little-endian float32 arrays；
- 1 independent analyzer process，不导入 adapter implementation，重新打开全部 EXR 并 byte-exact 重建 arrays；
- 总计 19 个唯一 child PID、0 source `.blend`、0 external asset。

两次 source decoded Combined/Depth/Vector/Object Index 必须 exact；两次 adapter arrays 必须 exact。multipart 名称冻结为 `BFS_F32_MASTER.Combined`、`Depth`、`Vector`、`Object Index`，通道、shape 与 finite state 逐项验证。

## 判定

37 个 attacks 覆盖 parent/D10 negative identity、freshness、tool/runtime/disk、typed float32 canonicalization、one-ULP、non-float exactness、scene/action/render、process/PID、multipart、repeat、independent payload oracle、Vector pair/sign/component、D9 coordinate conversion、static、Depth、ownership/orientation、adapter replay、diagnostics、operation boundary 与 result self-hash。

任一 base gate 或 attack 失败，结论必须为 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_F32_HOLDOUT_NOT_SUPPORTED`，保留 counterexample，禁止接入 D9.1。全部通过才允许 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_F32_HOLDOUT_SUPPORTED`，且只晋级 opaque orthographic integer-motion adapter contract。

即使通过，也不支持 perspective、subpixel、deformation、transparency、multi-owner、Cryptomatte、hair、volumetric、DOF、motion blur、跨版本/平台等价、真实 beauty temporal accumulation、电影感或人类偏好。下一步仍须另行预注册真实 textured render → adapter → D9.1 accumulator → Raw EXR bridge 的端到端 holdout。

Formal output root：`experiments/blender-multipart-temporal-adapter-f32-holdout-v0-1/`；预注册时不存在。D10.1 renderer、adapter、analyzer、runner、audit、preflight 与 tests 在预注册时也全部不存在。
