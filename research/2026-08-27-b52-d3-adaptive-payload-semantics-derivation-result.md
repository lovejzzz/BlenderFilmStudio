# B52-D3：adaptive payload task-semantics 派生结果

日期：2026-08-27

判定：`ADAPTIVE_PAYLOAD_SEMANTICS_DERIVATION_USABLE`

Future holdout candidates：`[]`

## 结论

D3 是一次有效的零重渲染派生，但没有一个 B52-D2 profile 同时通过两个构图的 Cryptomatte、Normal 与 Vector 任务分类器。这个结果不会改变 D2 的 `NATIVE_CPU_ADAPTIVE_PRODUCTION_HOLDOUT_NOT_SUPPORTED`，也不构成 production-safe tolerance。

正式分析直接使用 Blender 5.2 自带 Python 3.13、OpenImageIO 3.1.13.1 与 NumPy 2.3.4；打开 54 个已保留 EXR，分析 16 个 candidate–baseline pair，写出 18 张 PNG 与 18 个 canonical sidecar。Blender processes、renders、network calls、model calls 均为零。

## 身份与重复门

- 54/54 EXR container identity 重新匹配；
- 54/54 八个 decoded subimage roster 完整且 finite；
- 18/18 profile × variant 三重复在八个 decoded parts 上 exact；
- 两个 baseline Cryptomatte manifest 在各自 27 个 run 内一致，结构检查全部通过；
- D2 的阴性 verdict、null selection、null base failure、22 attacks 与 PASS audit 原样保留。

TABLETOP 的 baseline foreground 为 93,497 pixels，1 px 膨胀边界为 10,180，stable interior 为 86,840。INTERIOR 全幅 147,456 pixels 均为 foreground，边界为 7,089，stable interior 为 140,367。

## Cryptomatte

只有两个 pair 通过派生分类器：

- `ADAPT_T015_M0 × TABLETOP_WIDE`；
- `ADAPT_T020_M0 × TABLETOP_WIDE`。

16/16 pair 的 stable-interior confident dominant-ID mismatch 都为零；所有可见对象的 stable-interior hard-matte mismatch 也为零，changed alpha 的一像素边界局部化均为 100%。这说明 D2 的 matte 差异确实位于冻结的边界域。

阻断来自幅值而不是 interior topology。最温和的 INTERIOR `0.015/min0` worst alpha maximum 为 `0.0703125`，超过冻结的 `0.05`；TABLETOP `0.015/min32` 已达到 `0.0520833`。更宽松 profile 的 p99 或 maximum 继续上升。全图 unit-contrast composite 没有把这些 outlier 消失掉。

## Normal

Normal 为 0/16。所有 pair 的 stable-interior valid-vector mask mismatch 都为零，但：

- angular p99 从约 `1.12e-5°` 到 `0.503°`；
- angular maximum 从 `3.55°` 到 `11.65°`，16/16 均超过冻结的 `2°`；
- changed-pixel boundary localization 只有 `8.55%–41.59%`，低于 95%；
- five-probe Lambertian maximum 为 `0.0599–0.1518`，远高于 `1/255`。

因此不能把 Normal 差异描述为只有 ID 编码或无任务影响。诊断图显示较强误差主要沿几何/遮挡轮廓出现，但“看起来像边缘”不能覆盖 count-based stable-interior 反例，也不能改写已冻结分类器。

## Vector

Vector 也为 0/16，但失败形态与 Normal 不同：

- 两个 endpoint pair 的 worst p99 不超过约 `5.51e-5`，远小于 `1/1024`；
- absolute maximum 不超过约 `1.22e-4`，远小于 `1/64`；
- TABLETOP stable-interior support mismatch 为零；
- INTERIOR support mismatch 为 `530–890` pixels；
- changed-pixel boundary localization 只有 `3.19%–6.61%`。

所以 Vector 的幅值门全部通过，但 exact nonzero-support/count-localization 门拒绝。它提示下一研究应在实现前冻结 magnitude-weighted 与实际 Vector Blur 输出任务，而不能事后把任意非零 float 差改成可忽略。

## 审计

- result SHA-256：`a4da9fe19e08e5181bc75723fa04ab5961fbe1c48f25748a56a65e75df429739`；
- receipt SHA-256：`337d2c3a54b4818164b77cb894a9802d86219ea4db12d76f8dc7e0cc96439952`；
- audit SHA-256：`c1b9c61cbef701f58797d3ddc898cb54e3d10b52a3b422abfddf3e21b37bd5cc`；
- analyzer replay byte-exact；
- 5/5 frozen tools match；
- 54/54 EXRs match；
- 18/18 PNG 与 18/18 sidecar 在 formal/replay 两个目录中 byte-exact；
- 13/13 attacks；
- audit `PASS`。

## 下一门

B52-D4 应保持零重渲染并预注册两个更接近真实 downstream 的问题：

1. Normal/Vector 的误差幅值能量有多少位于边界，而不是只计算任何非零 float 的像素数量；
2. candidate Vector 经固定参数的 deterministic warp / Vector Blur surrogate 后，输出误差是否仍超过生产阈值。

如果 D4 仍拒绝，则 data/aux passes 必须继续使用 production baseline，adaptive 优化只能在 beauty-only 分流架构中研究。即使 D4 支持某个 payload profile，INTERIOR beauty 仍需新的 `0.01–0.015` fresh-seed 细曲线；D3 不能替代该 holdout。

机器证据：`experiments/adaptive-payload-semantics-derivation-v0-1/`。
