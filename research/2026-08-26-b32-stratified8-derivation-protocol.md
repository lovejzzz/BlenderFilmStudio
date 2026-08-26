# B32.1 protocol · deterministic eight-point stratified jitter derivation

日期：2026-08-26（America/New_York）
状态：`PREREGISTERED_EXPLORATORY_DERIVATION`

## 问题

B32 四点对称等权 ensemble 在 frame 37、72、103 上保持 A/B float exact，但 edge-reference RMSE 仍为 NATURAL32 的 `1.1887–1.2751×`，渲染时间约 `4.093×`。本次探索问：一个预先选定、中心对称的 8-point stratified candidate 是否在保持 exact A/B 的同时，以额外约 2× 候选成本带来足够大的 edge-reference 改善。

这仍是 derivation，不是未见帧确证。本文必须在 renderer、analyzer 和新输出存在前提交。

## 冻结候选

在 `[-0.5, 0.5) × [-0.5, 0.5)` sample square 的 4×4 格子中选中心对称的 checkerboard 八点：

| id | jitter U | jitter V |
|---|---:|---:|
| S1 | -0.375 | -0.375 |
| S2 | -0.375 | 0.125 |
| S3 | -0.125 | -0.125 |
| S4 | -0.125 | 0.375 |
| S5 | 0.125 | -0.375 |
| S6 | 0.125 | 0.125 |
| S7 | 0.375 | -0.125 |
| S8 | 0.375 | 0.375 |

八点权重均为 `0.125`，在 scene-linear RGB 中合成。点集质心为 `[0,0]`，每个点都存在对应的反号点。它是一个工程候选，不宣称最优 quadrature。

## 冻结设计

- 场景、Blender 5.2 build、OCIO、32-sample Eevee、fixed 8 threads 与 B31/B32 一致；
- frames 固定为 `37, 72, 103`，因此仅用于与已有 derivation 直接比较；
- replicate A/B 各使用 8 个全新 Blender PID，共 16 PID、48 次 EXR32 render；
- 复用已封存 B31 NATURAL32/CENTER32/NATURAL1024 与 B32 QUADRATURE4 本地原始输出；
- edge mask 仍是 dual-NATURAL1024 mean 的 RGB central-difference magnitude top 5%；
- 记录 Q8/NATURAL、Q8/CENTER、Q8/Q4 的 edge RMSE ratio，Q8/NATURAL global ratio，A/B RMSE 与实测 render seconds；
- reference 是 proxy，不是 truth；不运行 temporal 或 human review。

## 预写判定

按以下优先级判定：

1. 任一 A/B composite 不是 float exact：`REJECT_Q8_REPEATABILITY_FAILURE`；
2. 任一帧 Q8 edge RMSE 高于 Q4，或 mean Q8/Q4 edge ratio 高于 `0.90`：`RETAIN_Q4_DIMINISHING_RETURN`；
3. 每帧 Q8/NATURAL edge ratio 都不高于 `1.10`：`PROMOTE_Q4_Q8_COST_CURVE_NEAR_NATURAL`；
4. 其余满足稳定与至少 10% mean edge 改善的情况：`PROMOTE_Q4_Q8_COST_CURVE_PARTIAL`。

`PROMOTE` 只表示两个候选一起进入新 frame 正式 holdout，不表示 Q8 已可生产。Q8 的 8× 渲染成本不能被误写为“免费的质量改善”。

## 失败与非声明

- 如果无法使用新 PID、原始 EXR 不完整、identity 不匹配、点集/帧/权重被改写，结果 invalid；
- derivation frames 已被 B31/B32 使用，不能当成 holdout；
- 数值 RMSE 不等于可见质量、时序稳定或电影感；
- 本实验不比较 motion blur、Cycles、denoising、完整镜头或人类偏好。
