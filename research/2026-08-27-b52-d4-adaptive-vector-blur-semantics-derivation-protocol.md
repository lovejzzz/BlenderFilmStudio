# B52-D4 · Blender 5.2 Vector Blur 任务语义派生协议

日期：2026-08-27  
状态：**PREREGISTERED — 不得在看到正式 compositor 输出后改门槛**  
机器规格：`specs/adaptive-vector-blur-semantics-derivation.v0.1.json`

## 1. 为什么是这一门

B52-D2 是有效阴性：相对显式 `adaptive=true / threshold=0.01 / min=0 / max=128` production baseline，八个候选没有一个通过两场景完整合同。B52-D3 随后用零重渲染任务派生证明：

- Normal 的最大角度和五方向 Lambertian probe 均有明确反例；
- Cryptomatte 只在两个 TABLETOP pair 通过；
- Vector 的 endpoint p99 和 absolute maximum 全部远低于冻结幅值门，但 exact nonzero-support 与 changed-pixel count localization 全部失败；
- 因此 D3 仍然得到空的 future-candidate list。

Vector 现在存在一个可检验的歧义：很多极小非零像素是否真的改变了它的指定下游任务，还是 exact support-count 对浮点微差过敏。D4 只研究这件事，不重开 Normal、Crypto、INTERIOR beauty 或 D2 的 production 结论。

## 2. 预注册前的 Blender 5.2 接口探针

在任何正式 D4 输出或 candidate measurement 之前，五个只读/无渲染 Blender 进程用于确认接口：

1. 旧式 `Scene.use_nodes` + `Scene.node_tree` 在本机 Blender 5.2 失败；`use_nodes` 只留下弃用警告，`node_tree` 已不存在。
2. 5.2 的有效路径是新建 `CompositorNodeTree` data block，再赋给 `Scene.compositing_node_group`。
3. `CompositorNodeVecBlur` 的冻结 socket identifier 为 `Image`、`Speed`、`Z`、`Samples`、`Shutter`；后两项默认值分别为 32 与 0.5。旧式 node option properties 不存在。
4. D2 multipart EXR 在 `CompositorNodeImage` 上暴露 Combined、Depth、Normal、Vector、三层 Crypto 与 Sample Count 的完整 socket roster。
5. factory default compositor device 是 GPU；正式实验改为显式 CPU、FIXED 四线程，排除 Metal/GPU 调度变化。

失败的旧 API probe 没有被删除。完整观察保存在 `experiments/adaptive-vector-blur-semantics-preflight-v0-1/observation.json`。它只证明接口边界，不证明 headless Vector Blur 已可运行，也不包含任何正式候选输出。

Blender 5.0 migration 文档明确说明 compositor tree 已成为独立 data block、node options 迁移为 identifier-addressed inputs、Group Output 取代 Composite node。Blender 5.2 手册则规定 Vector Blur 的三个数据输入是 Combined Image、Vector Speed 和 Depth；Vector pass 的四分量来自前后帧的两组屏幕空间运动向量。来源：

- <https://developer.blender.org/docs/release_notes/5.0/migration/compositor_migration/>
- <https://docs.blender.org/api/5.2/bpy.types.Scene.html>
- <https://docs.blender.org/manual/en/5.2/compositing/types/filter/blur/vector_blur.html>
- <https://docs.blender.org/manual/en/5.2/render/layers/passes.html>

## 3. 问题与可证伪答案

问题：当 Combined 与 Depth 都固定为 production baseline 时，候选 Vector 是否会让 Blender 5.2 的冻结 Vector Blur 输出产生超门差异？把误差按幅值平方加权后，至少 95% 的 Vector 输入误差能量与 blur 输出误差能量是否都落在由真实运动半径扩展的边界影响域内？

允许两个结论：

- `ADAPTIVE_VECTOR_BLUR_SEMANTICS_DERIVATION_USABLE`：所有身份、运行、重复、任务测量、诊断与攻击合同成立；允许输出零个或多个 **Vector-only future contract proposals**。
- `ADAPTIVE_VECTOR_BLUR_SEMANTICS_DERIVATION_INVALID`：任一 base/evidence gate 失败；不得解释候选好坏。

“usable 且零 profile”是合法结果。任何通过 profile 也只是以后 fresh-seed holdout 的 Vector 合同提案，不能追认 D2/D3。

## 4. 输入隔离

矩阵为两场景 × 九 profile（一个 baseline + 八个 candidate）× 两个 fresh Blender repeats，共 36 个进程与 36 个 compositor EXR。

每一个 cell 都严格使用：

- `Image`：该场景 `PROD_T010_M0_R1` 的 Combined；
- `Depth`：同一 baseline EXR 的 Depth；
- `Speed`：该 cell profile 的 repeat-1 Vector；
- baseline cell 的 Speed 也来自 `PROD_T010_M0_R1`。

候选 Combined、Depth、Normal、Cryptomatte 与 Sample Count 一律不得进入 graph。这让输出差异只归因于 Vector payload，而不是 D2 已知的 beauty/Depth 差异。两个 compositor repeats 重复使用同一源 EXR，只检验 Blender 5.2 compositor 的 fresh-process 复现。

## 5. 冻结 Blender graph

每个进程从 factory startup 开始，不打开任何 source `.blend`：

1. 创建空场景与一台生成 camera；
2. `BLENDER_WORKBENCH`、512×288、100%、1:1 pixel aspect、transparent film；
3. compositor device CPU，FIXED 4 threads；
4. 新建 `CompositorNodeTree`，赋给 `Scene.compositing_node_group`；
5. 两个 Image nodes 分别加载 baseline EXR 与 speed-source EXR；
6. 连接 baseline Combined → `VectorBlur.Image`、speed-source Vector → `VectorBlur.Speed`、baseline Depth → `VectorBlur.Z`；
7. `Samples=32`、`Shutter=0.5`；
8. `VectorBlur.Image` → Group Output 的第一个 color socket；
9. 写出 RGBA32 ZIP OpenEXR。

`bpy.ops.render.render` 会被调用 36 次以驱动 compositor 与 Group Output，因此收据必须如实记录 36 次 Blender render calls；但不打开 source scene、不使用 Cycles，也不做新的 path-tracing sample。正确说法是“零新 Cycles sampling”，不是“零 render calls”。

## 6. 重复与有效性门

两次 fresh-process 输出必须在 decoded float32 RGBA 上 shape、finite mask 和每个值 exact。EXR container bytes 不要求一致；如 capDate 等 metadata 变化，只记录，不能代替像素判定。

为避免用无运动图证明“Vector 无影响”，两个场景的 baseline Vector Blur 输出都必须相对 baseline Combined 至少出现一个 RGB absolute error 大于 `1/65536` 的像素。否则 task 不具信息量，实验 INVALID。

正式运行前重新核验 D3 四个父文件、接口 preflight、本机 Blender、ACES 2 OCIO 和 54 个 D2 EXR 的 exact identity。运行后再次核验所有 parent/source EXR 未变。

## 7. magnitude-weighted 影响域

仍沿用 D3 的 Cryptomatte boundary seeds，但不再固定一像素边界。每个场景从 baseline Vector 计算：

`motionMagnitude = max(norm(X,Y), norm(Z,W))`

`radius = ceil(maxFinite(motionMagnitude) × 0.5) + 1`

然后以 Chebyshev distance 扩展 boundary seeds。半径最小 1、最大 64；若实际需要超过 64，实验 INVALID，不能事后扩大区域。

候选 Vector 的逐像素输入误差为两组 endpoint Euclidean error 的最大值，能量为 float64 累加的误差平方和。总能量恰为零时，influence fraction 定义为 1。报告 p50/p95/p99/max/RMSE、`1/65536` 与 `1/4096` 两个 active thresholds、总能量、影响域能量及 stable-interior 能量。

## 8. Blender Vector Blur 输出门

候选-speed 与 baseline-speed 输出比较使用 scene-linear RGB；逐像素误差是三通道最大绝对差。每个 pair 必须同时满足：

- Vector 输入误差能量影响域份额 ≥ 95%；
- blur RGB p99 ≤ `1/1024`；
- blur RGB absolute maximum ≤ `1/255`；
- blur RGB RMSE ≤ `1/4096`；
- alpha absolute maximum ≤ `1/65536`；
- blur 误差能量影响域份额 ≥ 95%；
- 影响域外 RGB error > `1/4096` 的像素为 0。

同一 profile 只有在两场景都过门且两次 compositor 输出 decoded exact 时，才进入 `vectorTaskTolerableProfiles`。这些是预先冻结的工程阈值：一 code-value maximum、sub-code p99、quarter-sub-code RMSE 和沿用 D3 的 95% localization。它们不是人类不可见阈值。

## 9. 诊断与审计

三档 profile（`0.015/min0`、`0.02/min32`、`0.05/min32`）× 两场景 × 两种 map，共 12 张 RGB8 PNG：

- Vector endpoint error，固定 `[0, 1/1024]`；
- Vector Blur RGB maximum absolute error，固定 `[0, 1/255]`。

编码固定为 `t=clip(value/max,0,1)`、RGB=`(t,t²,0)`、round-to-nearest uint8；每图有 canonical JSON sidecar。网页图只用于定位，正式判断来自 float32/float64 数组。

独立 audit 必须重新运行 analyzer，验证 byte-exact result、36 个输出、12+12 个诊断文件、冻结工具、父输入与 19 项攻击。19 个攻击覆盖 parent/artifact、Blender、OCIO、5.2 RNA、graph、input isolation、进程、退出码、输出、重复、baseline effect、两类测量、诊断、分类、operation boundary、immutability 与 self-hash。

## 10. 明确不主张

D4 不主张：

- D2/D3 任何候选被追认；
- production-safe adaptive profile；
- 物理 3D motion blur 等价；
- 四通道 previous/next pair 的方向命名；
- 人类不可见；
- 消除 Vector Blur 手册明确提示的遮挡、相机外信息与分层合成伪影；
- candidate Combined/Depth、Normal、Crypto 或 INTERIOR beauty 合格；
- unseen seed/frame/scene、2K、4K 或成本收益。

下一步顺序固定：提交并推送本协议 → 冻结 compositor runner/analyzer/audit/tests → 零正式输出预检 → 执行 36 个真实 Blender 5.2 compositor 进程 → 独立重放与审计 → 只按冻结门报告结果。
