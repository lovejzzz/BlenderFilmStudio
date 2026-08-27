# B52-D8 · External canonical warp → Blender Raw EXR bridge 协议

日期：2026-08-27

## 为什么改变边界

D7 的两个独立 reference 在全部六个 fixture 上逐 byte 一致，Blender 也跨净进程完全复现；但 Blender Bilinear 在四个高频/Repeat 边界用例上违反冻结的 p99/RMSE 分布门，因此不能成为通用 temporal warp consumer。D8 不调宽阈值，也不再要求 Blender 计算 warp。它把像素计算放到 Blender 外部，只问 Blender 能否作为精确的 float32 传输与后续场景管线边界。

预注册之前完成了一个明确标为 development-only 的真实 Blender 5.2 探针。37×23 RGBA 含负 RGB、RGB>1 和非不透明 alpha；外部 FLOAT/ZIP/Raw EXR 经 `Image → Group Output` 后解码，3,404 个标量全部逐位相同。这个观察只用于确认正式问题可运行，不能计入任何正式 gate。

## 双独立 producer 与 canonical 身份

三个未见 fixture 分别覆盖 signed HDR + Clip、113×67 高频 + Extend、以及四边唯一 sentinel + destination-varying Repeat。Python scalar producer 与 Node JavaScript producer 只共享冻结 spec：两边独立生成 source、displacement 和最终 Bilinear RGBA；输入先存为 float32，计算时提升至 float64，按固定四 tap 顺序累加，最终只 cast 一次 float32。

每个输出的 canonical 身份是 top-left、row-major、RGBA little-endian float32 bytes 的 SHA-256。每个 fixture 的 Python 与 Node `.rgba32` 必须 byte exact，否则实验在 Blender 运行结果之前即失败。

## EXR encoder 边界

每份 canonical raw 由一个独立 Python/OpenImageIO 进程写成四通道 FLOAT、ZIP、Raw EXR，并立刻重开解码。decoded bytes 必须与 raw 完全相同。这里不要求 EXR container bytes 相同，因为 header 与压缩实现不是像素身份。

正式边界共六个 encoder 进程：3 fixture × 2 producer。它们既验证外部计算到 EXR 的无损桥，也保留 producer 路径差异，不让一个共享容器掩盖错误。

## Blender 5.2 真机矩阵

每份 producer EXR 进入两个全新的 Blender 5.2 后台进程，共 12 个 Blender 进程。固定 factory startup、disable autoexec、CPU compositor、单线程、Raw input 和 RGBA32 ZIP EXR output。compositor 只有一个输入 image 与一个 group output，唯一 link 是：

`BFS_D8_EXTERNAL_SOURCE.Image → BFS_D8_GROUP_OUTPUT.Socket_0`

不打开 `.blend`，不运行 Cycles ray render；每个进程只打开其生成的外部 EXR 并进行一次 compositor render。连同 3 Python producer、3 Node producer、6 encoder，正式矩阵共 24 个唯一 PID。

## Exact gate 与攻击面

正式结果必须同时满足：

- Python/Node canonical raw 对每个 fixture 完全相同；
- 六份 EXR encode→decode 与各自 raw 完全相同；
- 十二份 Blender output 解码后与各自 raw 完全相同；
- 每个 producer-fixture 的两次 Blender 输出相同，两条 producer 路径最终也相同；
- changed scalar=0、maximum absolute error=0；
- negative、HDR>1、alpha、orientation/edge sentinel 在输入与输出均存在且位置和值完全一致；
- graph/RNA、24 PID、12 compositor calls、0 Cycles renders、roster/hash 和六对 diagnostics 全部精确。

24 个 adversarial attacks 必须能从独立 synthetic-valid evidence 被逐项触发，避免早期失败掩盖后续 validator。独立 audit 必须重放 Python/Node producer、encoder 和 analyzer，并逐 byte 核验正式 artifacts。

## 判定边界

全部 gate 与 attack 通过才可写 `EXTERNAL_CANONICAL_WARP_BRIDGE_SUPPORTED`。该结论只说明：在冻结的一个-link Blender 5.2 Raw float32 compositor 边界里，外部 canonical warp 可以无像素改变地进出 Blender。

通过后仍须单独预注册 layer/depth-aware external temporal accumulation；失败则把最终像素合成与 master EXR 留在 Blender 外部。D8 不证明 Blender Bilinear、任意 compositor node、depth、occlusion、motion blur、denoising、Cycles、生产镜头、电影感或人类偏好。
