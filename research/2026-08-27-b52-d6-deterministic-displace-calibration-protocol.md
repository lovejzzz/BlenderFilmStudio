# B52-D6 · 独立确定性 Displace 校准协议

日期：2026-08-27

## 研究问题

D5 的移动 fixture 证明 Vector Blur 对真实运动有强响应，但静态负控的 Vector p99 噪声高于预注册门，因此该节点按规则退出本分支的 oracle 角色。D6 不修改这项负结论，也不再让 Blender 自己定义“正确答案”。它问一个更小、更可证伪的问题：独立 CPU 参考 warp 能否在预先冻结的坐标、采样和边界规则下，与 Blender 5.2 CPU compositor 的 Displace 节点逐 float32 完全一致？

## 预注册前探索

官方 Blender 5.2 文档将 Displace 描述为二维像素位移，并暴露 Nearest、Bilinear、Bicubic、Anisotropic 与 Clip、Extend、Repeat。真实 RNA 显示 5.2 的输入是 `Image / Displacement(NodeSocketVector2D) / Interpolation / Extension X / Extension Y`；旧版 Scale X/Y 已不存在，旧 `Scene.node_tree` 也不存在，节点树绑定是 `Scene.compositing_node_group`。

探索过程保留两个失败：一次在同一 comprehension 中创建、枚举并立即删除三个节点时以 exit 139 崩溃；一次在绑定 ACES 2.0 OCIO 后请求不存在的 `Non-Color` 枚举而在渲染前失败。单节点只读 RNA 探针随后成功，数据色彩空间冻结为 `Raw`。

8×6 实际 compositor 探针得到逐 float32 零误差：正 X 位移令解码图像向右移动；正 Y 在 top-left 解码坐标中令图像向上移动；因此目的像素 `(x,y)` 的源坐标为 `(x-dx, y+dy)`。半像素 Bilinear、Clip/Extend/Repeat、非均匀 step field、RGB 与变化 alpha 都与独立枚举结果完全一致。它们只决定正式协议，不进入正式结论。

## 独立参考定义

正式 raster 为 64×48 RGBA float32，解码坐标原点在左上，x 向右、y 向下，整数坐标命名像素中心。源图全部由二进制精确分数生成：`R=x/64`、`G=y/64`、`B=((3x+5y) mod 64)/64`、`A=min(1,x/16)`。

位移在目的像素处取值。源坐标严格为 `u=x-dx(x,y)`、`v=y+dy(x,y)`。Nearest fixture 只用整数位移。Bilinear 对 `(floor(u), floor(v))` 周围四个 RGBA tap 以可分离权重求和；每个 tap 独立执行边界规则。Clip 返回透明黑，Extend clamp，Repeat 使用欧几里得 modulo。alpha 与 RGB 一样作为独立 float32 通道采样。参考实现不能 import 或执行 Blender worker。

## 七个冻结 fixture

- `ZERO_NEAREST_CLIP`：零位移；
- `POSITIVE_INTEGER_NEAREST_CLIP`：`dx=5, dy=-3`；
- `NEGATIVE_INTEGER_NEAREST_CLIP`：`dx=-7, dy=4`；
- `SUBPIXEL_BILINEAR_CLIP`：`dx=1/2, dy=-1/4`；
- `DESTINATION_STEP_NEAREST_CLIP`：右半区 `dx=3`、左半区 0；上半区 `dy=-2`、下半区 `dy=1`；
- `POSITIVE_INTEGER_NEAREST_EXTEND`：与正整数 fixture 相同但两轴 Extend；
- `POSITIVE_INTEGER_NEAREST_REPEAT`：与正整数 fixture 相同但两轴 Repeat。

每个 fixture 由两个全新的 Blender 5.2 进程执行，共 14 个唯一 PID、14 次 compositor render、零次 Cycles ray render。每个进程从 factory state 生成内存图像，使用 Raw 色彩空间、CPU compositor、固定一线程，并写一个 RGBA32 ZIP EXR。节点只能是两个 Image、一个 Displace 和一个 Group Output。

## 冻结判定门

两个重复的 decoded RGBA float32 必须逐位完全一致；每个 Blender 输出也必须与独立 CPU 参考的 top-left、C-contiguous、小端 float32 字节 SHA-256 完全一致。因此 maximum absolute error 与 RMSE 都必须为 0，超过 `1/65536` 的像素必须为 0。零位移必须与 authored source 完全一致；六个非零 fixture 各自至少有 256 个像素越过 `1/65536`，最大变化至少 0.0625，防止“两个空实现相等”。

每个 case 固定产生 reference RGB 与 maximum-channel error 两张 PNG及其 sidecar，共 14+14。20 个攻击覆盖 parent/runtime、roster、PID、report self-hash、源/位移公式、RNA/graph、操作边界、输出、重复、reference、sensitivity、diagnostic 与 result self-hash。独立 audit 必须重放 analyzer 并逐字节核验。

## 判定与非主张

全部门通过才给出 `DETERMINISTIC_DISPLACE_CALIBRATION_SUPPORTED`，并只允许下一步预注册 depth/layer-aware temporal accumulation。失败给出 `DETERMINISTIC_DISPLACE_CALIBRATION_NOT_SUPPORTED`，保留最早失败并决定缩小 primitive 或改用全外部 warp consumer。

D6 不是遮挡/深度正确性、motion-blur integration、Vector pass、adaptive sampling、production shot、电影感或人类偏好证据。它只校准一个可独立计算的二维采样 primitive。
