# B31 · fixed-jitter scene-linear edge-cost holdout result

日期：2026-08-26（America/New_York）  
预注册提交：`f11baac`  
正式工具提交：`48fadbf`  
冻结判定：`EDGE_REFERENCE_COST_SUPPORT`

## 正式执行

六个全新 Blender 5.2 PID 按冻结 schedule 执行 NATURAL32 A/B、CENTER32 A/B、REFERENCE1024 A/B。每个进程依次渲染未见 frame 10、44、86、120，共 24 次 scene-linear EXR32 render。四帧与 derivation 的 37、72、103 以及 B30 的 38 完全分离。

固定 `.blend`、BuildPlan、structure、ReviewRenderSpec、Blender binary、ACES 2 OCIO、Eevee、dither 0、Fast GI、TAA reprojection、FIXED/8 threads、960×540 与 motion blur off。六个 PID 唯一，源 `.blend` 未保存，23/23 个预注册攻击达到预期 reason。

## reference proxy 可靠性门

每帧 reference proxy 是两个独立 NATURAL1024 scene-linear RGB 的逐像素平均。edge ROI 按预注册规则从 reference mean 计算：RGB Euclidean central-difference magnitude ≥ per-frame 95th percentile，每帧 25,920 pixels。

REFERENCE1024 A/B edge RMSE ÷ NATURAL32 mean edge RMSE 的冻结上限为 0.05。正式观察：

- frame 10：`0`；
- frame 44：`0.00045276`；
- frame 86：`0`；
- frame 120：`0.00055488`。

四帧全部远低于上限，reference proxy reliability gate 通过。它仍是稳定代理而非 ground truth。

## 主结果

每帧 CENTER32 / NATURAL32 edge RMSE ratio：

| frame | NATURAL edge RMSE | CENTER edge RMSE | ratio |
|---|---:|---:|---:|
| 10 | 0.00890651 | 0.02550486 | 2.8636× |
| 44 | 0.01195950 | 0.02836478 | 2.3717× |
| 86 | 0.01321538 | 0.02866781 | 2.1693× |
| 120 | 0.01451588 | 0.03591649 | 2.4743× |

四帧全部超过冻结的 ≥1.5 门，最小值 `2.16927649`，均值 `2.46973077`。没有 frame <1.0 的方向反转反例。因此正式 decision 是 `EDGE_REFERENCE_COST_SUPPORT`。

全局 RMSE ratio 为 `1.4005–1.5581×`，non-edge ratio 为 `1.0767–1.0907×`。更大的相对误差集中在冻结的 high-gradient ROI。CENTER32 A/B 在四帧全部 float exact；NATURAL32 仅 frame 10 有非常小的 A/B 差，其余 exact。稳定性与 reference error 再次同时成立，互不抵消。

## 独立审计

正式 analyzer 在新的 factory-startup Blender 进程中对冻结 index 独立重跑，输出与接受的 analysis 字节一致，SHA `2614f98671947099a6964da25ab7f4b5637d3c672d3b3b2bf877d48c721a07e0`。正式 result SHA 为 `4fcc066fae67d61bda44b6c38bfa227f7af453e259a0620bd13ea59545790c56`；analysis binding SHA 为 `90d2f3fcb0d29c4d876e8858fb85320f186a838f1cd4a5d886c4f2e7b7ad8c6e`。

## 能说与不能说

可以说：在四个未见 frame 上，CENTER32 相对一个通过严格 A/B reliability gate 的双 NATURAL1024 proxy，逐帧增加了至少 2.169× 的 scene-linear edge-reference RMSE；derivation 的方向和保守效应门得到 holdout 支持。

不能说：“CENTER 肉眼画质差 2.17 倍”、reference 是真值、edge mask 是视觉系统、误差一定表现为可见 aliasing，或这一比率普适。没有 spatial supersampling、完整 temporal sequence、显示校准或独立 observer。B26 human review 保持 `PENDING`。

## 工程结论与下一边界

单点 CENTER 不应直接成为生产默认值：它以可重复性换取了可证实的 edge-reference 数值代价。下一可证伪方向不是放弃稳定性，而是构造 deterministic multi-jitter ensemble：用多个各自稳定的 fixed offsets 独立 render，再在 scene-linear 域按冻结权重合成。B32 应比较 4-point / 8-point ensemble 与 NATURAL32、NATURAL1024 proxy 的 edge error、strict repeatability 和 4×/8× render cost；候选点与权重必须先 derivation 后 holdout。

Artifacts: `experiments/sampling-quality-holdout-v0-1/results.json`, `experiments/sampling-quality-holdout-v0-1/evidence/`, `specs/sampling-quality-holdout-spec.v0.1.json` and `research/2026-08-26-b31-sampling-quality-holdout-protocol.md`.
