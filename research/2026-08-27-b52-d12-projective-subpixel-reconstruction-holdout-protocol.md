# B52-D12 · 刚性平面透视/亚像素重建 fresh holdout 协议

日期：2026-08-27  
状态：`PREREGISTERED_BEFORE_FORMAL_TOOL_OR_OUTPUT`

## 研究问题

D11.1 只支持每个 Vector 分量距最近整数不超过 `1/1024` 像素的窄域。D12 不扩大 rounding 半径，也不把整数 accumulator 偷换成任意浮点 consumer。它另起一个 fresh contract，问四件事：

1. 在真实 Blender 5.2 透视、刚性平面、真亚像素运动中，独立 pinhole/rigid-transform oracle 能否预测 Vector.XY endpoint；
2. Python 与 Node 两个独立 clip-bilinear consumer 能否逐字节给出同一 canonical float32 reconstruction；
3. reconstruction 能否在冻结绝对误差门下命中当前帧真实 Blender 连续纹理 beauty，并显著优于 nearest 与 wrong-sign controls；
4. 能否用当前局部表面点的上一帧相机深度预测值验证 history，而不是错误要求 previous Depth 等于 current Depth。

全部门通过才允许 `BLENDER_PROJECTIVE_SUBPIXEL_RECONSTRUCTION_HOLDOUT_SUPPORTED`。任一失败保留最早的冻结 base failure，并写 `NOT_SUPPORTED`。

## 为什么 depth 合同必须改变物理量

开发探针不是正式证据，但它给出了协议设计所需的反例：正确对应的刚性平面从相机深度约 10.00 移到约 9.82，直接前后 Depth identity 使 5,225/5,225 个正确 history pixel 全部失效。

D12 不调宽该阈值。它改为比较：

```text
sample(previous.Depth, q)
    vs.
depth_in_previous_camera(
  previous_object_transform(
    inverse(current_object_transform)(current_surface_point)
  )
)
```

这两个量描述同一个局部表面点在上一帧相机中的深度。直接 `previousDepth≈currentDepth` 被冻结为必须失败的 diagnostic control，不能参与有效性判定。

## Freshness

开发 probe 的 101×61、50 mm、36 mm sensor、轨迹、名称、ID 和纹理频率永久排除。正式矩阵使用从未渲染的 107×67、47 mm、35 mm sensor，以及四个新 fixture：

- `PROJECTIVE_OBJECT_DOLLY_TRANSLATE_107X67`：物体平移并改变深度；
- `PROJECTIVE_OBJECT_YAW_PITCH_107X67`：物体刚性 yaw/pitch，motion 与 predicted depth 都随像素变化；
- `PROJECTIVE_CAMERA_DOLLY_YAW_107X67`：静态表面、移动透视相机；
- `PROJECTIVE_STATIC_CONTROL_107X67`：相机与表面完全静止。

所有表面由 factory state 生成，是单 owner、不透明、足够覆盖画面的 tessellated plane。材质使用新的 Generated object-local 低频连续正弦 RGB emission，不打开图像纹理、源 `.blend`、灯光、DOF、motion blur、adaptive sampling 或 denoising。

## 独立投影 oracle

对 decoded top-left 像素 `(x,y)`，中心是 `((x+0.5)/W, 1-(y+0.5)/H)`。相机看向 local `−Z`，Euler 顺序冻结为 XYZ，horizontal sensor fit 的 `sensorHeight=sensorWidth·H/W`。

独立 analyzer 必须：

1. 从当前相机像素中心生成 world ray；
2. 与当前 rigid plane 相交；
3. 逆当前 object transform 得到 local surface point；
4. 应用 previous object transform；
5. 变换到 previous camera 并按 pinhole 投影。

冻结 endpoint 与 decoded sampling 约定：

```text
Vector.X = previousX - currentX
Vector.Y = currentY_top - previousY_top

q_x = currentX + Vector.X
q_y = currentY_top - Vector.Y
```

analyzer 禁止 import `bpy`、`bpy_extras`、`mathutils` 或两个 tested reconstructor；它必须独立实现 Euler matrix、ray/plane、rigid inverse 与 pinhole projection。

## Bilinear 与 metadata validity

previous linear RGBA 以 top-left、row-major、little-endian float32 解码。Bilinear 使用 `(floor(qx),floor(qy))` 的四 tap，固定累加顺序 `y0x0 → y0x1 → y1x0 → y1x1`。输入与坐标先提升 float64，只在最终 RGBA 写出时 cast 一次 float32；边界规则是 Clip。

测量 mask 同时要求：

- 当前像素距图像边界至少四像素；
- 四个 previous taps 全部在界内；
- current alpha 与四 tap alpha 都大于 0.999；
- current Object Index 与四 tap Object Index 全部严格等于 fixture pass index；
- current Depth 命中独立当前 ray-plane depth；
- bilinear previous Depth 命中 transform-predicted previous-camera depth。

本实验故意没有真实 occluder；ownership/depth 规则在单 owner 有效域内被验证，并通过 mutation attacks 证明 validator 有效。真实遮挡、disocclusion 与多 owner boundary 留给通过后的新 holdout。

## 冻结数值与感知代理门

每个 fixture 至少 4,000 个 valid pixel。三个 moving fixture 中至少 75% 的 measured XY components 必须距最近整数大于 `1/1024`，fractional-distance p50 至少 0.05。Vector endpoint 最大误差不超过 `1/1024` px，p99 不超过 `1/4096` px。

对 moving fixture 的 RGB reconstruction：

- maximum ≤ `1/512`；
- p99 ≤ `1/1024`；
- RMSE ≤ `1/4096`；
- 每通道 absolute signed mean ≤ `1/4096`；
- unit-range PSNR ≥ 72 dB；
- correct RMSE ≤ nearest RMSE 的 0.25；
- correct RMSE ≤ wrong-sign RMSE 的 0.10。

这些不是人类主观电影感指标，而是对连续、带限开发材质的冻结像素代理。静态 control 要求 reconstruction 与 current RGB 最大误差为零，Vector 最大残差仍只使用已有的 `1/1024` ceiling。

Python/Node reconstruction、mask 与 predicted-depth arrays 必须逐字节一致。编码后的 Raw float32 EXR 经两个 fresh Blender compositor bridge repeat 解码后必须逐 float32 完全一致。

## 正式进程与审计边界

正式矩阵固定 65 个 unique child PID：

- 16 个 Blender 5.2 Cycles source processes/renders；
- 8 个 multipart adapters；
- 8 个 Python 与 8 个 Node reconstructors；
- 8 个 Raw EXR encoders；
- 16 个 fresh Blender compositor bridge processes/renders；
- 1 个独立 analyzer。

正式运行不得调用模型或网络。Projected write 为 64 MiB，运行后必须仍保留 100 GiB disk reserve。57 个注册 attacks 覆盖 parent/freshness/runtime/process、scene/action、multipart、projection sign/origin/rotation/pixel-center、subpixel domain、bilinear tap/weight/boundary、dual implementation、owner/alpha/depth、quality controls、static、encoder/bridge、diagnostic 与 self-hash。

工具完成后必须先冻结 Git identity，再运行零 formal-output preflight；preflight 必须验证 formal root 仍不存在、所有工具匹配 Git blob、contract tests 与 Blender API/graph probe 通过、磁盘准入通过，才能创建 formal root 一次。

## 非主张与下一边界

D12 不修改 D11/D11.1，不支持曲面、变形、真实遮挡、disocclusion、多 owner、透明、Cryptomatte coverage、毛发、体积、motion blur、DOF、噪声 path-traced lighting、temporal accumulation、主观电影感、人物一致性、生产渲染或跨平台等价。

若 D12 支持，下一步才允许预注册真实 projective occlusion holdout：沿用 transform-predicted previous depth，加入显式 disocclusion rejection 与 multi-owner boundary policy；D12 的单平面结果保持为冻结 control。

## Pre-tool 状态

- formal root：不存在；
- preflight root：不存在；
- 11 个 formal tool paths：全部不存在；
- formal renders：0；
- formal measurements：0。

机器可读规范：`specs/blender-projective-subpixel-reconstruction-holdout.v0.1.json`；SHA-256：`dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2`。
