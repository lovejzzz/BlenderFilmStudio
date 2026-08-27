# B52-D10 · Blender 5.2 Vector / Depth / Object Index adapter 开发推导

日期：2026-08-27

状态：`EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE`
运行时：Blender 5.2.0 LTS，build `fbe6228777e7`，Cycles CPU，motion blur 关闭

## 问题

D9.1 已经证明：给定 previous/current RGBA、Depth、单一 ownership ID 和 current→previous motion，外部整数运动 temporal accumulator 能精确拒绝越界、遮挡与同 ID 深度交换，并且结果能无损经过 Blender Raw EXR bridge。但它刻意没有声明 Blender Vector 四分量的顺序、符号和单位，也没有声明 production multilayer EXR 的 pass 名称。

Blender 5.2 手册只公开说明 Vector 是“由下一帧和上一帧给出的两组屏幕空间二维运动”，没有规定 EXR 的哪两个分量对应哪一帧；同一页说明 Depth 是最近可见表面的距离，并说明 Vector pass 与 motion blur 不能同时使用。Object Index 是每个可见像素上的用户定义 ID，且不做抗锯齿。[Blender 5.2 Passes manual](https://docs.blender.org/manual/en/5.2/render/layers/passes.html)

本开发推导只回答：在一个可解析、opaque、正交、无形变的 Cycles fixture 中，真实 Blender 5.2 写出的四通道 Vector、Depth 和 Object Index 到底是什么。

## 为什么 D5 不能直接给出答案

D5 的物体和相机运动都关于当前帧对称。它证明了两对 Vector 都有强信号，但 `previous−current` 与 `current−next` 在这种轨迹上同号同幅，所以不能辨认 XY 与 ZW。D5 还保留了另一个重要反例：其静态 Cycles Vector 最大残差约为 `2.6702880859375e-5`，因此正式 adapter 不能把“逐位等于零”作为普适静态门。

D10 开发夹具改用不对称 XY 轨迹：

- `OBJECT_ASYMMETRIC_XY`：mover 在三帧的位置为 `(-0.50,+0.25) → (0,0) → (+1.25,-0.75)`；
- `CAMERA_ASYMMETRIC_XY`：camera 为 `(-0.40,+0.20) → (0,0) → (+0.80,-0.60)`；
- `STATIC_DEPTH_OWNERSHIP`：无 keyframe；
- 三个平面 pass index 固定为 `11 / 22 / 33`，相机空间深度固定为 `10 / 9 / 8`。

每个 fixture 都在一个全新的 Blender 进程中只渲染一次 192×108 RGBA32 ZIP multilayer EXR。投影候选由 Blender 的 `world_to_camera_view` 在开发阶段导出，所以它只能用于推导映射，不能充当未来 holdout 的独立 oracle。

## 首次分析失败与真实通道名

分析器第一版按 Blender 历史内部 pass 名 `IndexOB` 查找 ownership，真实文件却没有这个 subimage，分析立即以 `missing or malformed pass: BFS_MASTER.IndexOB` 停止，没有生成 observation。

逐 subimage 检查显示 Blender 5.2 实际写出：

1. `BFS_MASTER.Combined`：RGBA；
2. `BFS_MASTER.Depth`：Z；
3. `BFS_MASTER.Vector`：XYZW；
4. `BFS_MASTER.Object Index`：X。

因此 Python API 是 `use_pass_object_index`，而 EXR 公开名称必须冻结为 `Object Index`，不是 `IndexOB`。修正只发生在开发分析器，尚无正式 spec 或 formal root。

## 实测结果

九个 fixture/object 组合的候选聚合得到：

- `Vector.XY = previous_screen − current_screen`；
- `Vector.ZW = current_screen − next_screen`。

基于所有可见 Object Index 像素而非单点：

- 正确 XY 候选的最大端点误差为 `1.5686782979579906e-5 px`；
- 正确 ZW 候选的最大端点误差为 `2.1542276378777538e-5 px`；
- 开发夹具上的错误方向候选具有像素级到数十像素级误差；
- static fixture 的四个 Vector 分量在本次 192×108 渲染中全部为零，但 D5 的非零静态反例继续约束未来门；
- Depth 对相机空间 `10 / 9 / 8` 的所有 owner 像素最大绝对误差均为零；
- Object Index 对 `11 / 22 / 33` 的所有可见 owner 像素均为精确整数。

因此，连接 D9.1 的候选转换是：读取 current EXR 的 `Vector.XY`，并写入 D9.1 motion 数组 `(-X,-Y)`。原因是 D9.1 的数组坐标约定为 `q=(x−dx,y+dy)`，而 Blender Vector Y 使用屏幕向上的方向；取负两个分量后，D9.1 的 x 与向下图像行坐标都落到上一帧位置。

## 证据身份

- probe tool SHA-256：`d91174512c5e2670b530e003b416a10693a271e709dad788422454be9ba680b7`
- analyzer SHA-256：`c1d830ca4177fca3c22ec51f85a99cf97fba8a8f6ac133182ed68df4d98fd0ba`
- observation SHA-256：`303718b7d16f1a088c4c2d7f9d51e9cf66d178b5e00047843415388ae6f28693`
- OBJECT EXR：`26d0b18204d81e16da47bdf58a7465902527269da102d297d69592f965ee1fa8`
- CAMERA EXR：`7bf3eadcd360798b8d0cbca1811b4895b46215836f2e4e014d69468b1884781a`
- STATIC EXR：`6a37f645d4367a49dc695860a9075812633d383953436b77ca9188b4173ac3f6`

## 不主张

本结果不证明 perspective、subpixel、deformation、hair、transparency、volumetric、depth of field、motion blur、Cryptomatte、多 owner 像素或生产镜头。它也没有证明 adapter 实现正确，因为映射和开发夹具已经被观察过。

下一步必须先冻结一个全新分辨率、全新不对称轨迹和独立解析投影 oracle 的 D10 holdout；必须包含两个 fresh repeats、静态近零容差而非逐位零、错误 component/sign attacks、Depth/ownership attacks，以及 adapter 输出到 D9.1 文件布局的字节级复查。

Artifacts: `blender/probe_b52_d10_pass_adapter_source.py`, `scripts/analyze-b52-d10-pass-adapter-probe.py`, and `experiments/layer-depth-pass-adapter-development-v0-1/`.
