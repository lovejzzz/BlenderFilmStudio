# B32 formal result v0.2 · deterministic quadrature cost–quality curve

日期：2026-08-26（America/New_York）
状态：`FORMAL_REAL_BLENDER_HOLDOUT_COMPLETE`
判定：`COST_QUALITY_CURVE_SUPPORT`

## 先记录失败

v0.1 在完成 28 PID / 112 renders 后，因 frame 22 的 edge-mask quantile cutoff tie 违反 exact 25,920-pixel 合约，被封存为 `IDENTITY_OR_DESIGN_INVALID`，没有产生质量判定。

v0.2 在任何新 tooling/output 前将 mask 冻结为 exact total order：gradient magnitude 降序，tie 按 row-major flattened pixel index 升序，精确取 25,920 个。它改用全新 frames `31,67,109,143`，并从空 v0.2 work/evidence 目录重新执行全部 28 PID / 112 renders，没有复用 v0.1 输出。

## 正式观察

| frame | reference reliability | Q4 / NATURAL edge | Q8 / NATURAL edge | Q8 / Q4 edge | Q4 A/B | Q8 A/B |
|---|---:|---:|---:|---:|---:|---:|
| 31 | 0.00018667 | 1.2534× | 0.9448× | 0.7538× | 0 | 0 |
| 67 | 0 | 1.2456× | 0.9522× | 0.7644× | 0 | 0 |
| 109 | 0 | 1.2824× | 0.9496× | 0.7405× | 0 | 0 |
| 143 | 0.00052768 | 1.3010× | 0.9574× | 0.7359× | 0 | 0 |

reference reliability 四帧均远低于 `0.05` 门。Q4 和 Q8 composite 的 A/B scene-linear RMSE 每帧均为 0。

Q4/NATURAL edge ratio 的 mean 为 `1.27059`、maximum 为 `1.30097`，4/4 通过预写 `<=1.40` 门。Q8/NATURAL edge ratio 的 mean 为 `0.95102`、maximum 为 `0.95743`，4/4 通过 `<=1.10` 门。Q8/Q4 的 mean 为 `0.74868`，每帧都小于 1，通过 mean `<=0.90` 和 per-frame non-regression 门。

Q8/NATURAL global RMSE ratio 为 `0.9469–0.9527`；Q4/NATURAL global ratio 为 `1.0351–1.0505`。这些是同一 reference proxy 下的补充数值，不是额外主要终点。

## 成本轴

| cell | Blender render seconds | vs NATURAL32 |
|---|---:|---:|
| NATURAL32 A+B | 1.4915 | 1.000× |
| Q4 all components A+B | 6.0630 | 4.065× |
| Q8 all components A+B | 12.1443 | 8.142× |
| REFERENCE1024 A+B | 28.2609 | 18.948× |

Q8/Q4 实测 render-time ratio 为 `2.003×`。秒数只来自 Blender report timer，不包含调度、I/O、scene-linear 合成、长序列摊销或货币成本。

## 完整判定

五个 component verdict 全部为正：

- `REFERENCE_RELIABLE`；
- `Q4_Q8_EXACT_REPEATABILITY_SUPPORT`；
- `Q4_COST_POINT_SUPPORT`；
- `Q8_NEAR_NATURAL_PROXY_SUPPORT`；
- `Q8_OVER_Q4_DOMINANCE_SUPPORT`。

因此 overall decision 按预写规则为 `COST_QUALITY_CURVE_SUPPORT`。实验有效性检查通过：28 unique render PID、112/112 renders、112/112 outputs，29/29 negative attacks。一次新的 factory-startup Blender analyzer rerun 产生与封存 analysis byte-exact 的 SHA-256 `42cdbe6a…9c8b7`。

## 该如何解释

可以说：在冻结 Blender build、场景、机器、四个新 frame 与 scene-linear high-sample reference proxy 下，Q4 和 Q8 都精确重现；Q8 以约 8.14× NATURAL render time 在所有帧都达到预写 near-natural proxy 门，并且稳定优于约 4.07× 的 Q4。

不可以说：Q8 的肉眼画质比 NATURAL 更好、已达到电影级、时序已稳定、motion blur 正确、成本值得、或八点已最优。ratio 低于 1 是相对于一个 proxy 的数值，不是视觉真值。

下一个必要边界不是再添静态帧，而是完整连续序列：使用固定 Q4/Q8 点集渲染相邻帧，评估 temporal residual、边缘 flicker、motion blur 与 blind human review，同时保留 4×/8× 成本轴。

## 绑定

- result SHA：`94650057c2325844cd771a4806d241d206ecf20ddc159a48a44158840b1266bd`；
- analysis SHA：`42cdbe6a00fd15391af29a3c870771537e7fcc2e0a2bf1b210fb20abce19c8b7`；
- index SHA：`ef4d2f09ae697a3d59eca35ac0896ddcb54cb07639cbc7d5d22832954a5f5828`；
- binding SHA：`50f0b9dd2182ff722f4d63d07c18f88c7d4ffbd32bc52c521f072901a83576a4`；
- ledger SHA：`db542cb4cf60a4355ad97e043f5aa09c686e0706dfab86e4d9533498720ae962`；
- renderer SHA：`72391b713b3c021d0d313b0e9aef8a0f2780aa73fe2aaa377409349d091a6193`；
- analyzer SHA：`a8d9c8c4c4b5a14c4c6307cde69c222f0ee7622cf82690924d8a20bf544d97fd`；
- runner SHA：`52617c3c52b8ac3c4d69d586d7086bb01379e481b9e582b8e5f256bc59c09388`。

Artifacts: `experiments/quadrature-cost-holdout-v0-2/results.json`, `experiments/quadrature-cost-holdout-v0-2/evidence/quality-analysis.json`, `experiments/quadrature-cost-holdout-v0-2/evidence/analysis-binding.json`, `specs/quadrature-cost-holdout-spec.v0.2.json` and `research/2026-08-26-b32-quadrature-cost-holdout-v02-protocol.md`.
