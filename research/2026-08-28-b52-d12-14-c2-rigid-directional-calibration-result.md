# B52-D12.14-C2：三个 Material-owner directional domains 已由同一刚体平面实现

Date: 2026-08-28  
Classification: `PILOT_INFORMED_RIGID_FIXTURE_CALIBRATION_DERIVED`  
Verdict: `MATERIAL_OWNER_RIGID_DIRECTIONAL_CALIBRATION_CANDIDATES_DERIVED`  
Blender renders / EXR / model calls / network calls: **0 / 0 / 0 / 0**

## 结论

在预登记 commit `d1f4d9a` 与 tool-freeze commit `afd94d51bf085e10290f846d05903e92281dc3c2` 之后，正式 6-process matrix 从 500 个 world-space candidates 中机械导出 TOP、BOTTOM、NEITHER 三个候选。每个候选只使用一个固定 `[8,7]` local mesh，frame 0/1 scale 恒为 `[1,1,1]`；Blender probe 没有替换 mesh datablock。

这解决了 D12.12-H1 与 D12.14-C1 的实验域构造缺口：目标方向不再是对两张独立投影矩形的假设，而是由同一尺寸平面的世界位移或刚体旋转实际实现。它仍然不是 Blender render、Material Index pass 或 temporal reconstruction 的通过证据。

## 机械选择

| Target | Candidate | Current transform | Previous transform | Target / neighborhood | Non-target |
|---|---|---|---|---:|---:|
| TOP missing | `TOP-000153` | loc `(0,-3,4)`, rot `(0,0,0)` | loc `(0,-2.5,0)`, rot `(0,0,0)` | `187 / 187` | 0 |
| BOTTOM missing | `BOTTOM-000069` | loc `(0,2,3)`, rot `(0,0,0)` | loc `(0,2,0)`, rot `(0,0,0)` | `189 / 189` | 0 |
| NEITHER horizontal | `NEITHER-000113` | loc `(0,0,4)`, rot `(0,0,0)` | loc `(0.5,0,-1)`, rot Y `88°` | `15,113 / 15,113` | 0 |

TOP 的 current radius-2 / bilinear support / full stencil 为 `14,960 / 14,960 / 14,773`；BOTTOM 为 `21,546 / 21,546 / 21,357`。NEITHER 的 current radius-2 为 24,511、bilinear support 与 neither witnesses 都为 15,113、full stencil 为 0。三者的 target 之外 directional masks 均为 0。

NEITHER previous foreground 只有 262 pixels；它由同一平面在 frame 0 旋转到 `88°` edge-on，再在 current frame 回到 face-on，因而形成 common bilinear support 存在但 horizontal outer taps 双侧缺失的负控制域。

## 独立性与 Blender 证据

Python 与 Node 分别实现 binary64 Euler XYZ、bounded ray-plane intersections、nearest owner visibility、current-local → previous-world reprojection、previous owner raster、radius-2、bilinear floor 与 directional classes。500-row candidate table 和全部 selected masks byte exact；candidate table SHA-256 为：

`d92fc7a9ec26ce0186f0879c209d715d2281d5d715e1171b7cefbb1d48a7ba5f`

三个独立 Blender 5.2 factory-empty processes 对选中候选复用同一个 foreground mesh datablock。mesh identity、local-vertex hash 与 scale 都保持不变。Maximum scalar-vs-Blender projection errors：

- TOP: `1.0908596152603423e-5 pixel`
- BOTTOM: `1.2781884947798972e-5 pixel`
- NEITHER: `5.573793135482674e-6 pixel`

均低于在正式工具之前冻结的 `1/32768 = 3.0517578125e-5 pixel`。NEITHER 最大 RNA transform error 为 `3.003596038553269e-9`，最大 world-corner error为 `5.4045198982777265e-8`；其余两项为 0。

## Evidence chain

- 6/6 unique child PIDs，全部 exit 0；
- runner evidence checks `8/8`；
- independent audit baseline `18/18`；
- concrete semantic mutations `64/64` detected；
- receipt valid；
- H1 formal tree 前后均为 `de1ac6a394a3963a158d0e3432d5dfb89aaf9a87`；
- formal root size 2.1 MiB，EXR count 0；
- free bytes `109,680,394,240 → 109,676,621,824`。

Formal process elapsed time：Python oracle `94.260744s`，Node oracle `9.536274s`，三个 Blender probes 约 `3.21s` each，audit `0.057294s`。运行时间只描述该机器和当前实现，不是算法质量指标。

## 可复核 hashes

- Spec SHA-256: `e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3`
- Result file / self: `005d4338ccd0c7e791b3279517b3a3c1f7590eb20739f997d94f4358bcd79f96` / `7f6270a24d4c57218034401a9821aac1e39e649324ad33ac2b1d9e0c4a1bde8f`
- Audit file / self: `0e4c0f514ed469ed09c6582d4f2369339dfaa4b653dfcd3d1fc18fd1be8f38f5` / `6a1c20d463cc4148677101eeffb7350f6c0aeb6e13c6dfc9f5332a4577604fd8`
- Execution file / self: `86870d88fe65422bfbcda6cd49c07afb2f78ef39f279626b1db3ca34fa8b76b3` / `04b82b594a68813e52fd10917486fd5a6af0c2e09aba502a17d65d4e9996f925`
- Receipt file / self: `373706abc369cb3a09017cb88a1d6de51de8ea314f0c0999ed9c1aed27f669d4` / `e2a6cc139972ee9120ed70edc3b79df7b8378ae26badcb145409aabcf474d4c7`

## 不声称与下一门

本结果不证明 Cycles raster edge、Vector pass、Material Index、RGB error、risk threshold 或 factor-1 candidate。它也不覆盖非平面、变形、透明、hair、volume、motion blur、DOF、lighting 或 denoising。

下一门必须是另行预登记的 fresh Blender 5.2 rendered holdout：绑定这里的三个 world transforms，但使用新 raster sizes、新 Material/Object tokens、新 Generated signals 和新 output root；至少两次 clean repeats，并继续保留 Python/Node/independent auditor。只有真实 passes 与 analytic owner masks 对齐后，才能重新检验 one-sided candidate。D12.13 的 risk-tightness decomposition 仍是独立机制研究，不能混入同一 holdout。

Artifacts: `experiments/blender-material-owner-rigid-directional-calibration-v0-1/`.
