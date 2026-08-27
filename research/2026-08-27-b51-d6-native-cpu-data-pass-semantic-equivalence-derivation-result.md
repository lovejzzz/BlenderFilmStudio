# B51-D6：native CPU data-pass 语义等价派生结果

日期：2026-08-27

类型：`ZERO-RERENDER CRYPTOMATTE / DEPTH DERIVATION`

判定：`CPU_DATA_SEMANTIC_SAMPLE_REDUCTION_NOT_OBSERVED`

## 结论

按预注册的生产语义门槛，1–64 spp 仍不能替代 128 spp CPU data。两个已知构图的 `semanticDataSampleFloor` 都是 `128 spp`。因此当前“低 sample CPU Depth/Cryptomatte + Metal beauty”路线没有获得成本上的证据支持；B51-H2 不应按这个假设继续消耗新渲染。

D6 比 D5 更接近实际合成任务：它没有把 Cryptomatte ID float 当作连续数值，而是依照 Cryptomatte 1.2.0 规范，将 `CryptoObject00/01/02` 解码成六组 ranked ID/coverage，并按 manifest 重建每个对象的 matte。Depth 则分离了 `1e9` 以上背景 sentinel、前景拓扑和主对象 coverage ≥ 0.999 的稳定表面。

## 冻结门槛

Cryptomatte 对每个 128-spp parent 可见对象要求：

- alpha 0.5 hard matte：0 个错位像素；
- parent dominant coverage ≥ 0.5 的像素：0 个 dominant-ID 错位；
- matte 最大绝对误差 ≤ `1/255`；
- matte p99 绝对误差 ≤ `1/1023`；
- 全帧 matte RMSE ≤ `1/4095`。

Depth 要求前景/背景 mask 逐像素一致；稳定表面 p99 绝对误差 ≤ 1 mm、最大绝对误差 ≤ 1 cm、p99 相对误差 ≤ `1e-4`。边界混合像素的单一 Z 数值不被冒充为稳定对象深度。

## 64 spp 反例

64 spp 是最接近 128 spp 的低剂量，但两个构图仍同时违反 Cryptomatte 和 Depth 门槛：

| Variant | dominant ID mismatch | hard-matte mismatch 合计 | worst matte max / p99 / RMSE | Depth foreground mismatch | stable Depth p99 / max |
|---|---:|---:|---:|---:|---:|
| TABLETOP_WIDE | 10 | 53 | 0.09375 / 0.010417 / 0.002745 | 56 px | 2.802 mm / 6.074 mm |
| INTERIOR_CHAIR | 102 | 205 | 0.15625 / 0.023438 / 0.005299 | 0 px | 73.200 mm / 182.019 mm |

TABLETOP 的最大稳定 Depth 误差仍在 1 cm 内，但 p99、相对误差和前景拓扑失败；INTERIOR 的稳定表面误差远超门槛。64 spp 的 matte 最大误差也不是轻微编码扰动，而是 0.09375–0.15625 alpha。

32 spp 更差：TABLETOP / INTERIOR 的 dominant-ID mismatch 为 15 / 114，hard-matte mismatch 合计为 83 / 231；INTERIOR stable Depth p99 为 73.135 mm、最大为 184.865 mm。

## 数据完整性

- 32/32 D5 EXR byte identity match；
- 32/32 Cryptomatte metadata 合同有效且 manifest 在各 variant 内一致；
- unresolved active IDs：0；
- coverage 越界、sum 超限、rank 逆序、重复 active ID：全部 0；
- TABLETOP manifest 8 个对象、128-spp 可见 5 个；INTERIOR manifest 15 个、可见 9 个；
- 两个 128-spp reference 继续逐 float 复现 H1 CPU parent；
- 16 个 dose-repeat 对继续在四个 data passes 上 exact；
- 新 Blender processes：0；新 renders：0；输入 EXR 修改：0。

## 审计与失败保留

正式结果 base failure 为 `null`，16/16 attacks 通过。独立审计 PASS：analyzer replay byte-exact，2/2 frozen tools、4/4 D5 bindings 与 32/32 artifacts 全部 match。

第一次 analyzer invocation 写入了一个不存在的完整 tool-freeze SHA。数值计算虽然完成，但被冻结为 `TOOL_FREEZE_COMMIT_IDENTITY` 失败并在审计前拒绝；无 Blender、无 render、无 EXR 修改。C1 只修正为实际 Git object `bd82b15840115655fb4f508177b6024c722ccbd6`，没有改变 spec、threshold 或工具字节。

## 证据身份

- result SHA-256：`f79eb1d82e537c9f46e490a76d37e3125651581c9dace8674c2d443e55a47d85`；
- audit SHA-256：`0d4fd7252535044eecd4cfecc9f4636cca1eaa36760795b1a96ad71e1906da15`；
- evidence-core SHA-256：`ce71f20f429fb5d555fc2bbcd78725222efbb57621bd551c559356287bc9329d`；
- preregistration commit：`b17e2a3fdd11605f13b912bab256befa6579510a`；
- frozen tool commit：`bd82b15840115655fb4f508177b6024c722ccbd6`；
- runtime：Blender Python 3.13.13 / OpenImageIO 3.1.13.1 / NumPy 2.3.4。

## 决策

停止把 H2 当作当前 split-production 的下一步：在 exact 和已冻结的 production-semantic 两种合同下，128 spp 都是共同 floor。继续渲染 unseen split pairs 只会检验一个已经缺少成本优势的路径。

Metal 仍然有价值，但边界收窄为：快速 preview、look development，或 beauty-only 候选；不能把它描述为当前统一 production EXR backend。接下来的成本研究应转向单一 CPU production path 的真实优化变量，例如 adaptive sampling、受控 denoising/quality profile 和 native CPU resolution scaling，并保持 B50 人工电影感门槛独立为 0/18 pending。

Artifacts: `experiments/native-cpu-data-pass-semantic-equivalence-derivation-v0-1/`, `experiments/native-cpu-data-pass-semantic-equivalence-tool-identity-failure-v0-1/`, `specs/native-cpu-data-pass-semantic-equivalence-derivation.v0.1.json`, `research/2026-08-27-b51-d6-native-cpu-data-pass-semantic-equivalence-derivation-protocol.md`, `research/2026-08-27-b51-d6-c1-tool-freeze-identity-correction-protocol.md`, `scripts/analyze-b51-native-cpu-data-semantic-equivalence.py` and `scripts/audit-b51-native-cpu-data-semantic-equivalence.py`.
