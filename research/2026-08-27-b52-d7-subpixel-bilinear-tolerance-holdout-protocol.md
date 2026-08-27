# B52-D7 · Subpixel Bilinear tolerance fresh holdout 协议

日期：2026-08-27

## 研究问题

D6 的七个真实 Blender primitive 中有六个对独立参考逐 float32 相同。唯一反例是 Bilinear：两个净进程完全复现，但相对冻结的 NumPy float32 参考最大误差 `1.758337e−6`，因此全套 exact 合同按规则判为 NOT SUPPORTED。

D7 不追认 D6，也不重复那组 `(dx,dy)=(1/2,−1/4)`。它问一个新的问题：在从未渲染过的位移、分辨率、alpha/频率结构和 extension 组合上，Blender 5.2 CPU Displace 是否始终跨净进程 exact，并与 Python 和 Node 两个独立 Bilinear reference 保持在 D6 输出前已存在的 `1/65536` 最大误差边界内？

## Freshness 与双参考

D7 不读取 D6 的 render 或 reference 作为输入。全部六个 displacement field、63×47 与 127×73 resolution、两种 source formula 都是 fresh。所有位移都含非整数分量，且没有任何 case 复用 D6 的位移 pair。

Python reference 与 Node reference 只能共享冻结 spec，不能 import 彼此代码。两者都先把 source 与 displacement 存为 IEEE-754 float32，再提升到 float64 计算四个 Bilinear tap，按 `y0x0/y0x1/y1x0/y1x1` 顺序累加，最后只 cast 一次 RGBA float32。Python 使用 scalar loops、`math.floor` 与 `struct.pack`；Node 使用独立 JavaScript loops、`Math.floor` 与 `Float32Array`。两份 canonical `.rgba32` 必须 byte exact，否则实验先在 `DUAL_REFERENCE_EXACT` 失败，不能拿 Blender 决胜负。

## 六个未见 fixture

低频 alpha-ramp raster 使用 63×47：

- Clip：`dx=1/4, dy=3/4`；
- Extend：`dx=−3/2, dy=1/8`；
- Repeat destination field：x 两区为 `3/8` 与 `−5/8`，y 奇偶行为 `1/4` 与 `−3/4`。

高频 alpha-checker raster 使用 127×73：

- Clip：`dx=−3/4, dy=3/2`；
- Extend：`dx=17/8, dy=−3/8`；
- Repeat destination field：dx 按 x mod 4 取 `[1/8,5/8,−7/8,3/8]`，dy 按 y mod 2 取 `[−1/8,7/8]`。

每个 fixture 各执行一个 Python reference 进程、一个 Node reference 进程和两个全新的 Blender 进程，共 24 个唯一 PID。Blender 侧固定 CPU compositor、一线程、Raw 内存输入、RGBA32 ZIP EXR；12 次 compositor render、0 次 Cycles ray render，不打开 `.blend` 或外部资产。

## 冻结 tolerance

每个 fixture 必须同时满足：

- Python 与 Node reference canonical float32 bytes 完全相同；
- 两个 Blender decoded outputs 完全相同；
- 相对双参考的 maximum absolute error ≤`1/65536`；
- RMSE 与 p99 scalar error 都 ≤`1/1048576`；
- 四通道 mean signed error 的绝对值都 ≤`1/1048576`；
- alpha maximum error ≤`1/65536`，越过 maximum gate 的像素为 0；
- 至少 50% 像素相对 authored source 越过 `1/65536`，最大变化至少 0.125。

`1/65536` 在 D6 正式输出前已用于 gate 与 diagnostic scale；D7 只是把它用于 fresh holdout。两个 `1/1048576` 分布门公开承认依据 D6 观测设定，因此不能由 D6 自身通过，必须由未见 D7 输出验证。

## 审计与判定

每个 fixture 输出 reference RGB 和固定 `1/65536` 标尺 error map，共 12 PNG 与 12 sidecar。23 个攻击覆盖三种 runtime、双参考、全部 roster/hash、source/field、Blender RNA/graph、repeat、maximum/distribution/bias/sensitivity 与 result self-hash。独立 audit 必须重放两个 reference 与 analyzer，并逐字节核验。

全部门通过才给出 `SUBPIXEL_BILINEAR_TOLERANCE_HOLDOUT_SUPPORTED`，且只允许晋级这一 tolerance-bounded Bilinear primitive。随后仍需单独预注册 depth/layer-aware temporal accumulation。失败则保留输出，改用全外部 warp consumer 或更窄的 passing subset。

D7 不修改 D6 的 exactness 负结论，不证明遮挡、深度、temporal integration、motion blur、Vector、adaptive sampling、production shot、电影感或人类偏好。
