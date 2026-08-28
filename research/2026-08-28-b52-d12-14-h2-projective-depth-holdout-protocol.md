# B52-D12.14-H2 · projective depth / Position control formal holdout protocol

Date: 2026-08-28
Experiment: `B52-D12.14-H2`
Classification: preregistered targeted Blender 5.2 holdout

## Question

在一个从未渲染过的 edge-on rigid fixture 上，`1 / bilinear(1 / Z)` 是否能恢复至少 1,024 个被 `bilinear(Z)` 拒绝的 same-Material structural cells；同时，Position pass 是否能把 Vector control 绑定到 Cycles 的实际 first hit，且所有 NEITHER-horizontal cells 仍然被 one-sided curvature 明确拒绝？

这不是 H1 的修复重跑。H1 保持 `scientificVerdict = null`；H2 使用新 experiment ID、新 trajectory selection、新 raster、新 signal、新 tokens、新 tessellation、新 seed 和全新的四次 Cycles renders。

## 为什么需要两条独立的修正

H1 partial evidence 显示两个不同问题。第一，perspective camera 下的 Depth 是 camera-space Z；跨像素线性插值 Z 不遵循投影几何，而 reciprocal depth 在同一四个 taps 上与 transform-predicted depth 对齐。第二，Vector 是从实际 `ShaderData.P` 计算的；integer pixel center 不是该 first-hit point。P1 的 Position pass development probe 已经支持用同一 world point重建 Vector control，但 P1 fixture 和 EXR 永久禁止成为 H2 measurement input。

H2 因此冻结为：reciprocal depth 是 decision candidate；direct Z 只是 paired control；Position 只进入 analyzer/auditor control，绝不进入 Python 或 Node consumer decisions。

## Fresh fixture

轨迹取自 C2 candidate table 中此前未被选中的 `NEITHER-000060`：current plane 位于 `[0,0,4]`，previous plane 位于 `[0,0,-1]` 并绕 Y 旋转 89.5°。H2 raster 固定为 `201x137`，foreground/background tessellation、Material/Object tokens、Generated emission、view layer 与 render seed 全部是新的。

预登记前运行了一次不保存输出的 Blender-bundled Python scalar pilot。它只调用冻结 C2 analytic raster functions，在 16 个新 raster 上检查 structural masks；选定 raster 的 analytic counts 为 current-radius2 `26,201`、bilinear support `13,034`、NEITHER `13,034`、full stencil `0`。该 pilot没有启动 Blender、没有 render、没有 EXR，也没有看到 H2 的 Depth、Position、Vector、Material、RGB 或 decision outputs。

## Frozen decision

对于 current cell，consumer只读取 Combined RGBA、Depth、Material Index 与 Vector XY。motion coordinate 为 `qx=x+vx, qy=y-vy`。四个 previous taps 必须同 Material、alpha > 0.999、Depth finite and positive。paired control 使用 `bilinear(Z)`；正式结构门使用：

`inverseDepth = 1 / bilinear(1 / Z)`

它必须满足：

`abs(inverseDepth - predictedPreviousDepth) <= max(1, predictedPreviousDepth) / 1024`

但 predicted depth 只由 analyzer 从 current Position、rigid transforms 与 camera projection计算；consumer不能读取 Position。consumer在 reciprocal-depth structural gate 通过后计算 radius-2 与 outer support。任何一行同时没有 left/right outer support时，cell必须进入 `one-sided-unavailable`，不得进入 risk 或 acceptance；fallback必须逐 byte 等于 current float32 RGBA。

## Confirmatory gates

- 每个 repeat 至少 1,024 same-owner bilinear cells。
- 每个 repeat 至少 1,024 reciprocal-depth-valid cells。
- 每个 repeat 至少 1,024 `inverse-pass AND direct-Z-fail` rescued cells。
- 每个 repeat 至少 1,024 reciprocal-depth-valid NEITHER-horizontal witnesses。
- NEITHER accepted 必须为 0，unavailable set 必须等于 NEITHER witness set。
- Position-derived current Depth、previous raster Vector 与 Vector ZW 必须分别满足固定 `1/16384` control tolerance。
- 两个 repeats 的 Combined、Depth、Position、Vector、Object Index、Material Index decoded arrays 必须 exact；EXR container bytes可不同，但 metadata difference 只允许 Combined 的 `Date`、`RenderTime`、`Scene`。
- Python 与 Node 的所有 control/decision arrays exact。
- 修改 current RGB 而保留 alpha及所有非 RGB inputs时，除 reconstructed fallback 外的 decisions exact。
- analyzer 与 audit 必须从真实 child records replay operation counts；不能 hardcode true。
- audit 至少执行 64 个独立 semantic attacks。

## Tool-failure protections

正式工具冻结后，zero-render preflight必须调用 analyzer 的 probe-shaped schema smoke，确保 analyzer后来读取的每个 source/adapter/consumer/execution key都已经被 synthetic records走过。runner必须在任何 child failure 的 finally path写出 self-hashed `execution.json`、`failure.json` 和 `receipt.json`，保留所有已存在 evidence，并把 scientific verdict设为 null。

preflight通过并提交之前不得创建 formal root。formal run 只能创建四次新 Blender Cycles CPU renders：2 frames × 2 clean repeats。若失败，保留失败根，不修改工具，不用相同 ID 重跑。

## Interpretation boundary

SUPPORTED 只说明：在这一条 fresh opaque rigid-planar emission trajectory上，reciprocal depth能够恢复目标 structural domain，Position可以作为 control oracle，而 NEITHER cells仍被安全拒绝。它不测量被接受 RGB 的质量，不证明 TOP/BOTTOM one-sided reconstruction，不覆盖复杂电影场景，也不允许直接进入 compiler。

H2结束后，研究主线回到 `SceneSpec → immutable BuildPlan → Blender 5.2` 最小编译器的 B01/B02 两次净构建结构哈希复现。任何 H2 算法进入编译器，必须另有 compiler-stage integration preregistration。
