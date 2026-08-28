# B52-D12.14-P1：Position pass 解决了 H1 的 Vector oracle 样本错位

Date: 2026-08-28

Status: `DEVELOPMENT COMPLETE`

Scientific verdict: none

Development verdict: `POSITION_PASS_ORACLE_DEVELOPMENT_SUPPORTED`

## 结果

在 preregistration commit `15a4f19` 与 tool-freeze commit `0a7ed9b` 之后，runner 创建 fresh P1 root，并完成两个新的 Blender 5.2 Cycles CPU current-frame renders 与一个 analyzer child。3/3 children exit 0，14/14 development gates 成立。

| measurement | observed |
|---|---:|
| foreground Position pixels | 27,383 |
| pixel-center Vector error max | `5.7715910e-4 px` |
| Position-based Vector error median | `7.9499049e-6 px` |
| Position-based Vector error p99 | `2.4902754e-5 px` |
| Position-based Vector error max | `3.2810152e-5 px` |
| frozen gate | `6.103515625e-5 px` |
| Position-derived Depth error max | `0` |
| next Vector magnitude max | `0` |

实际 Position 投影的 current raster 相对 integer pixel center 在 X/Y 方向分别偏移约 `5.07e-4`–`5.56e-4 px`。这个量级与 H1 pixel-center Vector mismatch 相符；把同一个 Position world point 送入 current/previous rigid projection 后，最大误差下降约 17.6× 并通过原 gate。实测支持的解释是：H1 比较了不同采样位置，而不是 Blender Vector pass 在这条路径上违反刚体投影。

## Repeat 与 container identity

两次 EXR container SHA-256 不同，但六个 decoded subimage arrays——Combined、Depth、Position、Vector、Object Index、Material Index——全部 byte exact。唯一 metadata differences 位于 Combined subimage，字段精确为 `Date`、`RenderTime`、`Scene`；其余 subimages 无差异。这支持 H2 使用 canonical decoded-pass digest 作为 repeat identity，并把 container bytes 与 allowlisted metadata 单独报告。

## 与 inverse depth 的关系

P1 没有重新测量 inverse depth。H1 postfailure replay 已显示，edge-on plane 上 `bilinear(Z)` 的 median/max error 为 `0.381959` / `0.465232`，而 `1 / bilinear(1/Z)` 为 `2.754e-5` / `1.884e-4`，并把 NEITHER radius-2 witnesses 从 270 恢复为 16,065。P1 只解决 Vector control oracle；inverse-depth 是另一项 algorithm change，仍需要 fresh H2 fixture 和正式预登记。

## 被保留的工具覆盖缺口

冻结 analyzer 将 `OPERATION_BOUNDARY` 直接设为 true，没有在 analyzer 内 replay source report counts 或 runner children。这不是 measurement 值造假：posthoc independent check 直接验证了两份 source reports 各自恰有 1 Blender process、1 render、1 Cycles render、0 model/network calls，runner 恰有两个 source children 与一个 analyzer child，3/3 exit 0，所有 log hashes 和 execution counts 一致。但该补充检查不是 preregistered P1 gate；H2 必须把它变成可执行 gate。

## 证据身份

- result file SHA-256: `69edb9ad3db3c67b5b21ad3b3a4c9e0ab59e05e29d38a60a34ce9ae04457b9fa`
- result self-hash: `c3d8b7226872702d3947320ed19dbeed80b19704adf9432dbc2505e4abcd534e`
- execution file SHA-256: `5ecde80477a2372d7c837b34a38f83fe67449baf453329cfd1a787149aeb6618`
- execution self-hash: `ecfca1e8b24b65c71e3fe4ea1f28b0b188d0071d5d633f8ac2d75fa0a72cd944`
- receipt file SHA-256: `b24e63690338b33b09d915c771795f2e57e69c612b50ce48116b4d518979c203`
- receipt self-hash: `4b805e0f513100b836867c017cab1fa07cf8101a9c8b4fd75fef68b9871e40e8`

## 下一边界

P1 允许 H2 把 Position 用作 source-control oracle，但 Position 仍禁止成为 reconstruction decision input。H2 必须使用新 experiment ID、fresh camera/fixture/raster/tokens/signals/seed/output，预先冻结 inverse-depth structural gate、decoded-pass digest、analyzer-on-probe schema smoke、real operation replay 与 failure finally-path；任何 H2 rendered output 只能在 exact spec 与 tool-freeze commits 都推送后产生。
