# B31 · fixed-jitter scene-linear edge-cost holdout protocol

日期：2026-08-26（America/New_York）  
状态：`PRE-REGISTERED · NOT YET EXECUTED`

## 问题

B30 已证明 CENTER32 的严格 repeatability；B31 derivation 又在三个 frame 上观察到 CENTER32 相对双 NATURAL1024 reference proxy 的 edge RMSE 是 NATURAL32 的 2.1876–2.2623 倍。正式 B31 问：这个方向和保守效应门能否在四个未见 frame 上同时复现？

主张被严格限制为“scene-linear edge-reference error cost”。它不是肉眼 aliasing、锐度或电影感判断。

## derivation / holdout 分离

derivation frames 是 37、72、103；正式 holdout frames 在任何 formal output 前冻结为 10、44、86、120，并排除 B30 的 frame 38。derivation 的六个 PID 与所有 EXR 不进入正式样本。

预注册时，正式文件 `blender/render_b31_sampling_quality_holdout.py`、`blender/analyze_b31_sampling_quality_holdout.py` 与 `scripts/run-b31-sampling-quality-holdout.mjs` 均不存在。正式工具只能在本提交后实现。

## 六进程设计

按 `NATURAL32_A, CENTER32_A, REFERENCE1024_A, NATURAL32_B, CENTER32_B, REFERENCE1024_B` 启动六个全新 Blender PID。每个 PID 依次 render 四个 holdout frame，合计 24 次 render 与 24 个 scene-linear EXR32。

- NATURAL32：32 samples，hidden jitter property absent；
- CENTER32：32 samples，`override_pixel_jitter_sample=[0,0]`；
- REFERENCE1024：1024 samples，property absent。

所有 cell 固定同一 `.blend`、BuildPlan、structure、ReviewRenderSpec、Blender 5.2 binary、ACES 2 OCIO、Eevee、dither 0、Fast GI、TAA reprojection、FIXED/8 threads、960×540 与 motion blur off。源 `.blend` 不保存。

## 参考可靠性先于结果

每帧 reference proxy 是两个独立 NATURAL1024 RGB 的逐像素平均。先在该均值上计算 RGB Euclidean central-difference magnitude，取 ≥95th percentile 的 25,920 个像素作为 edge ROI。

正式比较前必须通过 reference gate：REFERENCE1024 A/B 的 edge RMSE ÷ NATURAL32 mean edge RMSE ≤0.05，且 NATURAL denominator >0。任何 frame 失败都判 `REFERENCE_PROXY_UNSTABLE`，不能继续宣传 CENTER cost。

## 冻结主终点

每个 frame 分别计算 NATURAL32 A/B 对 reference mean 的 edge RMSE 平均，以及 CENTER32 A/B 的对应平均；主 ratio 为 CENTER/NATURAL。

- 四帧全部 ≥1.5：`EDGE_REFERENCE_COST_SUPPORT`；
- 任一帧 <1.0：优先 `EDGE_COST_DIRECTION_REVERSED`；
- 一至三帧 ≥1.5、无反转：`MIXED_EDGE_REFERENCE_COST`；
- 零帧 ≥1.5、无反转：`EDGE_REFERENCE_COST_NOT_REPRODUCED`。

1.5 是从 derivation 最小值 2.1876 向 no-effect 收缩的保守 holdout 门。四帧必须逐一通过；均值不能掩盖一帧反例，结果后不得改阈值。

## 非主张

即使四帧支持，也只能说 CENTER32 在这些 frame 上相对这个稳定 reference proxy 增加了冻结 ROI 的 scene-linear error。reference 不是 ground truth，没有空间超采样；ROI 不是人眼模型；没有 temporal playback 与独立 observer。因此结果不能改写为“固定 jitter 画质差 1.5 倍”或“不可用于电影”。

正式规范：`specs/sampling-quality-holdout-spec.v0.1.json`。
