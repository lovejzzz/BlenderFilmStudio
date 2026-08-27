# B51-H1：Native Metal production holdout 预注册协议

日期：2026-08-27  
状态：`PREREGISTERED_HOLDOUT`  
实验：`B51-H1`

## 问题

B51-D1 证明本机 warm Metal 对两个简单场景的 render operator 约为 `0.57–0.72 s`，同时发现 Metal 重复并非 strict-float exact。B51-D2 又否证了精确用户级 `~/.cache/cycles` 缺失足以造成 D1 的 `108.31 s` synchronization 事件。

本实验不继续解释该历史极端值，而是把 readiness 变成 fail-closed 合同：只有独立 Metal canary 先进入冻结同步与总耗时区间，四个未在 D1/D2 中渲染过的确定性构图才可进入 holdout。

## 先验冻结的未见构图

源 `.blend`、绑定哈希与 OCIO 身份保持不变；所有变化只发生在每个 Blender 子进程的内存中，绝不保存回源文件。

1. `TABLETOP_WIDE`：相机平移、52 mm、静物组旋转 `+8°`、主光 `×1.25`。
2. `TABLETOP_TIGHT`：相机平移、68 mm、静物组旋转 `−6°`、轮廓光 `×1.35`。
3. `INTERIOR_CHAIR`：相机平移、64 mm、椅子平移与旋转 `+10°`、窗光 `×0.82`。
4. `INTERIOR_WINDOW`：相机平移、78 mm、椅子平移与旋转 `−8°`、窗光 `×1.30`。

所有对象名、浮点操作数、cell 顺序、采样与输出 pass 已写入 `specs/native-metal-production-holdout.v0.1.json`。工具提交不得修改这些值。

## 运行矩阵

- `CANARY_METAL`：`256×144 / 16 spp / Combined`，必须在任何正式 cell 之前运行。
- 每个未见构图：`CPU ×1 + Metal ×2`。
- 共 `13` 个新的原生 Blender 5.2 进程；`12` 个正式 holdout EXR 均为 `512×288 / 128 spp / 7 subimages`。
- 禁止修改用户 cache、禁止写回源 `.blend`、禁止网络、下载、Docker 与模型调用。

## 冻结晋级门槛

Canary：

- EXR `Cycles` metadata 中 `synchronization ≤ 2.0 s`；
- render operator `≤ 2.0 s`；
- process wall `≤ 10.0 s`；
- 任一项失败立即停止，不能用后续热帧覆盖失败。

四个正式构图全部必须通过：

- CPU–Metal Combined：linear NRMSE `≤ 0.0065`；
- log-luminance RMSE `≤ 0.0016`；
- edge-linear RMSE `≤ 0.0060`；
- linear P95 absolute error `≤ 5e−7`；
- linear max absolute error `≤ 0.55`；
- Metal R1–R2 Combined：normalized RMSE `≤ 1e−4` 且 P95 `≤ 1e−6`；
- CPU–Metal 的 `Depth + CryptoObject00/01/02` decoded floats 全等；
- 每个 Metal 正式 cell render operator `≤ 2.5 s`；
- 所有要求的 pass 有限、设备/源/绑定/操作回放/进程身份正确。

阈值由 B51-D1 已观察包络预先导出，但不把 D1 的两个原画面计入 H1 证据。

## 结论边界

`SUPPORTED` 只允许 warm Metal 进入下一门：连续序列的热、功耗与内存压力，以及 macOS worker containment/recovery。它不等于无人值守生产授权，也不主张 2K/4K、角色、毛发、体积、人眼等价或跨机器泛化。

负结果必须保留。分析器修正若有发生，必须保留首次失败、限制修正范围，并从冻结证据独立重放。
