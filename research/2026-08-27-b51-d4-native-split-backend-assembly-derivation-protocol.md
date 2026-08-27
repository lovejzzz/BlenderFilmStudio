# B51-D4：Metal beauty + CPU data multipart EXR 组装推导协议

日期：2026-08-27

状态：`PREREGISTERED_DERIVATION`

运行边界：零 Blender、零重渲染、零 source EXR 修改

## 问题

B51-H1 已拒绝 CPU 与 Metal 共用 exact data-pass 合同；B51-D3 又显示 Cryptomatte 的差异稀疏且位于边界，而 Depth 是广域低幅漂移。下一候选不是放宽 H1，而是让每个 pass 留在有证据支持的后端：Metal 提供 Combined/Normal/Vector，CPU 提供 Depth/Cryptomatte。

本实验只问工程问题：能否把两份已验证、同场景、同帧、同采样的 multipart EXR 合成一份可追溯的新 EXR，并保证每个输出 float32 array 与被指定的 source pass 完全相同。

## 为什么先做 D4，而不是直接跑 H2

Multipart writer、subimage spec、Cryptomatte manifest 和跨源 metadata 是尚未验证的实现面。如果在未见正式构图渲染后才修改 merger，就会把工具开发与 holdout 结果混在一起。D4 只使用已知 H1 evidence，冻结并攻击合并语义；H2 才使用未见构图。

## 输入

使用两个互补的已知 pair：

- `TABLETOP_WIDE`：H1 beauty tolerance 通过；
- `INTERIOR_CHAIR`：H1 beauty tolerance 失败，作为“组装正确不等于 beauty 晋级”的保留反例。

四个 source EXR 的 SHA-256 与字节数已经写入 spec。H1 receipt/result/audit 与 D3 result/audit 也必须逐一匹配冻结身份。

## Pass routing

Metal：

- `BFS_MASTER.Combined`
- `BFS_MASTER.Normal`
- `BFS_MASTER.Vector`

CPU：

- `BFS_MASTER.Depth`
- `BFS_MASTER.CryptoObject00`
- `BFS_MASTER.CryptoObject01`
- `BFS_MASTER.CryptoObject02`

输出仍按原七层顺序写入。每层从所选 source 复制完整 ImageSpec 与像素，再增加确定性的 `bfs:*` provenance attributes。禁止修改或覆盖 source EXR。

## 对齐门

CPU 与 Metal source 必须在尺寸、data/full window、channel roster、float format、Camera、File、Frame、Scene、Software、pixel aspect、resolution、color interop 与 screen window 上 exact。Cryptomatte conversion/hash/manifest/name 必须 exact。只允许 Date、RenderTime 与 Cycles timing metadata 不同。

## 复现门

每个 pair 独立组装两次。两份输出必须：

1. container bytes exact；
2. 七层 roster 和 provenance 完整；
3. 每个输出 float32 array 与路由 source exact；
4. 所有值 finite；
5. 独立 audit 从冻结 source 与工具重新生成 receipt/result/四个 EXR，并逐字节一致。

## 判定边界

`NATIVE_SPLIT_BACKEND_ASSEMBLY_DERIVATION_USABLE` 只允许把 merger 冻结后送入 B51-H2。它不修复 H1 的 `INTERIOR_CHAIR` beauty 失败，不证明人眼等价、Cryptomatte/Depth 合成安全、长序列稳定或生产授权。

## 失败保留

第一次运行中的 writer、metadata、攻击或 audit 错误必须保留；修正只能追加新协议/结果，不能覆盖失败产物或回改本门。
