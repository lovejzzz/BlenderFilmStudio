# B30 · natural versus CENTER fixed-jitter intervention protocol

日期：2026-08-26（America/New_York）  
状态：`PRE-REGISTERED · NOT YET EXECUTED`

## 问题

B30 derivation 在一个 NATURAL PID 中复现两个自然 mode，同时三个固定 jitter cell 各自在单 PID 内 12/12 exact。正式 B30 问：`CENTER [0,0]` 能否在 12 个新 PID、共 144 次 render 中保持同一个冻结 decoded RGB identity，并由同规模 NATURAL cell 在至少两个独立 PID 内复现自然 mode switching？

这是一项干预确认，不是画质评测。CENTER 相对自然图像改变超过 13 万个 decoded pixels，因此即使稳定也不能称为无损修复或电影级默认值。

## derivation 与 confirmation 分离

四 cell derivation 永久保持 `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`。它只选择 CENTER 候选与 frozen hash，四个 derivation PID 不计入正式样本。

预注册时，正式文件 `blender/render_b30_jitter_intervention.py`、`blender/classify_b30_jitter_intervention.py` 与 `scripts/run-b30-jitter-intervention.mjs` 均不存在。正式工具只能在本 protocol 与 machine-readable spec 提交后实现。

## 设计

按固定顺序 `N01,C01,N02,C02,…,N12,C12` 启动 24 个全新 Blender 进程。每个进程设置 frame 38 一次并连续 render 12 次，总计 288 次 render、288 个 PNG。

- NATURAL：确保 scene 不含 `override_pixel_jitter_sample`；
- CENTER：在首次 render 前将该 property 精确设置为 `[0.0, 0.0]`。

其余输入完全相同：冻结 `.blend`、BuildPlan、structure、ReviewRenderSpec、Blender 5.2 binary、ACES 2 OCIO、Eevee 32 samples、dither 0、Fast GI、TAA reprojection、FIXED/8 threads、960×540、无 motion blur。源 `.blend` 不得保存。

## 冻结主终点

CENTER 严格稳定要求 12 个 CENTER PID 的 144/144 decoded RGB hash 全部等于 derivation 冻结 hash `ba0591ae…ff8aca`。任何一个不同 hash 都保留并优先判为 `CENTER_VARIATION`，不得用 RMS、容差或多数票救回。

NATURAL PID 必须在自己的 12 次调用中同时含冻结 REFERENCE 与 ALTERNATE 才算 switching PID。支持门槛为至少两个独立 NATURAL PID；一个是 inconclusive，零个表示 active control 没有在正式批次复现 within-PID switching。

NATURAL 第三 hash 优先判为 `NATURAL_MODE_SPACE_EXPANDED`。正式支持只有在 CENTER 144/144 exact 且 NATURAL ≥2 switching PID 时成立。288 张相关图不能被当作 288 个独立过程样本。

## 证伪与非主张

以下任一观察都阻止“严格稳定支持”：CENTER 任一第三 hash、NATURAL 任一第三 hash、自然对照不足两个 switching PID、进程/PID/cell 绑定失败、render 次数或顺序不符、identity/control 改变，或冻结的 attacks 未全部达到预期 reason。

即使结果支持，它也只说明本机器、本 Blender build、本 frame/scene/profile 上的 CENTER intervention 与严格 identity 相容。源码显示 override 还影响从 raw custom values 派生的其他 sample dimensions，因此不能把因果缩写成“仅 filter U/V”。更不能据此声称抗锯齿、感知质量、时间连续性或电影感提高；这些需要另一个独立冻结的质量与 human-review protocol。

正式规范：`specs/fixed-jitter-intervention-spec.v0.1.json`。
