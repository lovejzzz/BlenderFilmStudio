# B51-H1：Native Metal production holdout 结果

日期：2026-08-27  
状态：`NATIVE_METAL_PRODUCTION_HOLDOUT_NOT_SUPPORTED`  
运行：13 个新的 Blender 5.2.0 LTS arm64 进程  
审计：`PASS · 21/21 attacks · byte-exact replay`

## 结论

Metal 的 readiness 与 warm throughput 门通过，但冻结的跨后端图像契约没有通过。因此 B51-H1 不允许进入长序列生产压力测试，更不允许把 Metal 宣称为已晋级生产后端。

这不是运行失败。13/13 Blender 进程、源与绑定身份、设备选择、内存构图操作、EXR、有限值、无源文件修改和操作边界全部通过。失败来自真实像素证据：

1. 四个未见构图的 CPU–Metal `Depth` 均非 decoded-float exact。
2. 四个构图的至少一个活动 Cryptomatte 层也非 exact；这否证了把 D1/D2 的“Metal 重复内 exact”外推为“CPU–Metal 跨后端 exact”。
3. `INTERIOR_CHAIR` 的 CPU–Metal Combined linear NRMSE 为 `0.01259916`，超过冻结上限 `0.0065`；log-luminance RMSE `0.00351943 > 0.0016`，edge RMSE `0.01147864 > 0.0060`。P95 与最大绝对误差仍在门内，说明失败不是均匀全帧漂移，而需要空间定位。

## Canary 与速度

正式矩阵前的 Metal canary：

- render operator：`0.396386 s`；
- EXR synchronization：`0.14 s`；
- process wall：`1.164752 s`；
- 身份、profile、pass roster、artifact 与全部预算检查通过。

四个构图的 Metal R1/R2 render operator：

| Variant | Metal R1 | Metal R2 | CPU–Metal worst NRMSE | 结果 |
|---|---:|---:|---:|---|
| TABLETOP_WIDE | 0.524779 s | 0.547367 s | 0.00056648 | beauty tolerance pass；exact-pass fail |
| TABLETOP_TIGHT | 0.542486 s | 0.582294 s | 0.00027218 | beauty tolerance pass；exact-pass fail |
| INTERIOR_CHAIR | 0.751008 s | 0.674710 s | 0.01259916 | beauty tolerance fail；exact-pass fail |
| INTERIOR_WINDOW | 0.549164 s | 0.586695 s | 0.00026947 | beauty tolerance pass；exact-pass fail |

全部八个 Metal 正式 cell 都远低于 `2.5 s` 上限。每个构图的 Metal R1–R2 NRMSE 为 `5.4e−8–1.1e−7`，也远低于冻结的 `1e−4`。所以本次拒绝不是 Metal 热态速度或同后端重复稳定性造成的。

## 失败与修正记录

首次分析结果保留为 `results.initial-v0.1.json`。它给出正确负 verdict，但在已失败基线上运行攻击时，三个较晚的攻击被原 `EXACT_PASS_DOMAIN` 遮蔽，计数只有 `18/21`。C1 只把攻击副本的实际失败项临时归一为通过，以独立到达每个验证分支；正式证据、阈值和 base failure 未改。

首次独立审计随后暴露输出目录与 EXR 证据根耦合，失败保留为 `audit.initial-failure.json`。C2 只把证据根绑定到 receipt 父目录。修正后从冻结 receipt 与 13 个 EXR byte-exact 重放，原 tool-freeze Git blobs、父证据与运行前后源文件身份均匹配。

## 证据身份

- preregistration commit：`b2c053c0f2c4c498fd8123de628dd83ba76e9ebe`
- frozen tool commit：`fde45119082692d10815db6588c5b8424d2b849a`
- run receipt SHA-256：`42d9dff174378e90e724bae93f710df96e63cb3a0e18eeebd3958dd69d3d69cc`
- corrected results SHA-256：`9bcd9dea0ea071decfde1021195794837e088e57b0ef499a66159332ca86a8a9`
- corrected audit SHA-256：`f707b3d11aba424e4932f107561e205e6a7aa015d33d18f2346896b0ebb5edd3`

## 下一可证伪边界

先做 B51-D3 的零重渲染空间/域定位：量化 CPU–Metal Depth 与 Cryptomatte 的 changed-component 数量、误差幅度、边界关联，并定位 `INTERIOR_CHAIR` Combined 的异常区域。之后才能决定生产合同应当：

- 对 beauty 与 data passes 使用不同后端；
- 对 data passes 使用语义/边界容差而非 float exact；或
- 保持 CPU 作为 data-pass backend、Metal 只产 beauty。

在该分叉有证据前，不修改 H1 阈值，不执行长序列压力晋级。

## Artifact

- `specs/native-metal-production-holdout.v0.1.json`
- `experiments/native-metal-production-holdout-v0-1/run.receipt.json`
- `experiments/native-metal-production-holdout-v0-1/results.initial-v0.1.json`
- `experiments/native-metal-production-holdout-v0-1/results.json`
- `experiments/native-metal-production-holdout-v0-1/audit.initial-failure.json`
- `experiments/native-metal-production-holdout-v0-1/audit.correction-v0.2.json`
- `research/2026-08-27-b51-h1-c1-negative-baseline-audit-correction.md`
- `research/2026-08-27-b51-h1-c2-audit-evidence-root-correction.md`
