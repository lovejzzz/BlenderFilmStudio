# B51-D3：CPU–Metal pass 与空间差异定位协议

日期：2026-08-27  
状态：`PREREGISTERED_DERIVATION`  
运行边界：零 Blender、零重渲染

## 为什么现在不能进入长序列

B51-H1 的 canary、warm timing 和 Metal 重复通过，但四个构图全部违反 CPU–Metal exact data-pass 合同，`INTERIOR_CHAIR` 又超过三项 beauty 阈值。直接放宽门槛会把一个真实负结果改写成成功，因此下一步先定位差异。

## 冻结输入

只读取 H1 的 receipt、corrected result、corrected audit 与 12 个正式 EXR。每个 EXR 必须重新匹配 receipt 中的 SHA-256、字节数、512×288 尺寸、七个 subimage roster 与有限值。Canary 不进入定位矩阵。

## 数据通道边界

- Depth：对每个四邻域有限值 pair，若 `abs(a-b) > max(1e-3, 0.01 × min(abs(a), abs(b)))`，两像素记为边界；非有限状态不同也记边界。
- Cryptomatte：四邻域任一 float32 component 非 exact，两像素记为边界。
- CPU–Metal disagreement：Depth 或任一 Crypto pass 的任一 component 非 exact。
- data-pass localization：disagreement pixels 位于 CPU/Metal 边界 union 的一像素膨胀区内的比例。`≥ 95%` 标记为 boundary-localized，但这只是分类，不是 promotion。

## Chair beauty 关联

对 `INTERIOR_CHAIR / IC_METAL_R1`：

1. 计算 Combined RGB 每像素 squared-error energy 与 max-channel absolute error；
2. 将全部 Depth/Crypto disagreement union 膨胀两像素；
3. 测量落在该 mask 中的 beauty squared-error energy 比例；
4. `≥ 90%` 才标记与 data disagreement 空间相关；
5. 同时保留 `max-channel > 1e−3` 的像素数、bbox、连通域和最高误差坐标。

## 图像

生成五张可审计 PNG：四个 Metal R1 data maps，以及一张 chair beauty heatmap。所有像素映射公式已写入 spec，PNG 本身进入 evidence hash 和独立审计。

## 结论边界

本实验只回答“差异在哪里、是否贴近边界”。即使得到 boundary-localized，也不能说明 Cryptomatte 语义安全、Depth 可合成、人眼看不见或 Metal 已晋级。任何 beauty-Metal/data-CPU 分后端方案都必须另立新 holdout。
