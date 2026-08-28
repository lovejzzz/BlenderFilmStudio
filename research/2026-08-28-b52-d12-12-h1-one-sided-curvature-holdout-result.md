# B52-D12.12-H1：Material-owner one-sided curvature 新鲜 holdout 结果

Date: 2026-08-28

Classification: confirmatory Blender 5.2 holdout

Evidence status: execution/audit valid; candidate rejected

## 结论

冻结的 factor-1 one-sided curvature candidate 在这次新鲜 Blender 5.2 holdout 中得到：

`MATERIAL_OWNER_ONE_SIDED_CURVATURE_HOLDOUT_REJECTED`

这不是运行失败。24 个新 Cycles CPU renders、110 个唯一子进程、两套独立 consumers、第三套 analyzer replay 与独立 auditor 都完整结束；execution receipt 有效，audit baseline 为 21/21，93/93 个具体 mutations 被命名门拒绝。拒绝来自预登记 hard/directional gates 的真实反例。

## 三个独立失败面

### 1. Acceptance threshold 不能推出冻结的质量门

全局 accepted RGB maximum 为 `6.693601608276367e-05`，超过 `3.0517578125e-05`；RMSE 为 `4.868241720825754e-06`，仍通过。最坏像素位于 `NEITHER_HORIZONTAL_STRIP_185X117` 的 `(x=92,y=107,R)`：current 为 `0.506805419921875`，reconstruction 为 `0.5067384839057922`，实际误差 `6.693601608276367e-05`。

该像素的 risk 为 `125489 Q30 = 0.00011687073856592178`，低于冻结 inclusive threshold `131072 Q30 = 0.0001220703125`，所以 candidate 按规则接受它。Risk underbound RGB samples 为 0：risk 机制没有低估这个样本；失败是 policy coupling——允许接受的 risk threshold 是质量门的 4 倍。每个 repeat 在该 fixture 中均有 39 个 accepted RGB samples 超出质量门。

### 2. 两个竖向 fixture 没有生成预登记 one-sided domain

LEFT / RIGHT primary fixtures 分别生成 89 / 91 个 measurement-region directional eligible witnesses，全部被接受。TOP / BOTTOM primary fixtures的 directional witnesses、eligible 和 accepted 均为 0；两者所有 radius-2 cells 同时都是 full-stencil cells（17,325 / 18,511）。因此竖向 transform/raster/measurement 组合没有建立待测试的竖向单侧外 tap 条件。

这使 directional stress contract 失败。不能用“这些 fixture 的 coverage 为 1.0”替代方向测试，因为 coverage 全部来自 full-stencil domain。

### 3. Neither-side fixture 生成了另一种边界，而非 neither-side

`NEITHER_HORIZONTAL_STRIP_185X117` 在 measurement region 中产生 297 个 `RIGHT_MISSING_LEFT_AVAILABLE` cells，但 `neither-horizontal` witnesses 为 0。它的 radius-2 cells 为 791，accepted 为 13，另外 778 个由 risk 拒绝；13 个 accepted 来自 full-stencil 子域。预登记要求至少 1 个 neither-side witness 且该 witness set accepted=0，因此 negative-control gate 失败。

## 通过的证据门

- D12.11 与 D12.12-D1 parent bytes 和 formal Git trees 未变。
- 24 个 render、12 个 adapter、12 个 Python consumer、12 个 Node consumer、48 个 typed-envelope、1 个 analyzer、1 个 auditor，共 110 个唯一 PID，全部退出 0。
- Python/Node 19 个输出 arrays 全部 byte exact；两次 repeat 的 adapter/consumer arrays 全部 byte exact。
- 第三套 analyzer 对 projection、visibility、Material/Object identity、structure、directions、risk、reason、fallback 和 reconstruction 的 replay 全部 exact。
- Vector oracle mismatch 为 0；Material alias、false-invalid accept、risk underbound 均为 0。
- 四个 primary fixtures 的 accepted/radius-2 与每 owner retention 均为 1.0；static control accepted/radius-2 为 1.0 且 accepted delta 为 0。
- 独立 audit 为 21/21 baseline gates、93/93 concrete semantic mutations。

## Raw EXR repeat identity 的容器级反例

Repeat 1/2 的 10 个 canonical adapter arrays 全部 byte exact，覆盖 Combined RGBA、Depth、Vector XY/ZW、Object Index 和 Material Index。Raw multipart EXR SHA-256 不同；OpenImageIO metadata diff 将差异定位为每个文件的动态 `Date` 和含 `R1`/`R2` 的 `Scene`，另有一个 frame 的 `RenderTime`。文件尺寸逐对相同。

因此本次预登记的 raw-source byte identity hard gate正确地失败，但数据同时支持一个更精确的后续设计：把 deterministic pixel payload 与 nondeterministic container metadata 分开，或在 source 写出前冻结/剥离这些字段。不能事后改写本次 gate。

## 后续研究边界

本次结果不支持 factor 1 进入 nonplanar、lit 或 production compiler holdout。下一步应先分别预登记：

1. threshold/quality coupling 的 post-hoc derivation，检查把 Q30 acceptance threshold 收紧到质量门对应量级后，安全性与 coverage 的真实 trade-off；
2. 能在 radius-2 域内稳定产生 TOP/BOTTOM one-sided witnesses 的 fixture calibration，但 calibration 数据不得作为下一次 confirmatory measurement；
3. 真正产生 neither-horizontal witness 的几何构造；
4. EXR pixel payload identity 与 metadata-normalized container identity 的双层 determinism contract。

## Evidence identities

- Result file SHA-256: `175c6c568b60b29332954c9bd3f24634c4028aaf8a5c221fd999ad01acc9c0a7`
- Result self-hash: `c3c84f825b78ff4302fc6e65ff04956ac783a65dcc5ccf99fc1688bd5d15fdee`
- Audit file SHA-256: `d983482d6d0d752e268273487592a42a7700b121c8769195d49001bb2742c4e1`
- Audit self-hash: `bc7e90af03a631c6ae799581ff3e84a855f149bab28e1ba59fc43c709e922ab4`
- Execution file SHA-256: `babddc5c9849004c901d99d0c86f8b09d7d5696ad3b9149d5b5a5c99bcc6c935`
- Execution self-hash: `0798b9edf859d9e5cc19a9b5b5190383737e272388cf716be5fca0ef63c747ee`
- Receipt file SHA-256: `9b692d8945821c2458a41952cc3cecde73066703d603455a484d9d4d8b7d9b14`
- Receipt self-hash: `55c122a7ecd748b07cf2803b4694ba05d77b1f0833d9c4295d2fbbdc4d5a6830`

Artifacts: `experiments/blender-material-owner-one-sided-curvature-holdout-v0-1/`.
