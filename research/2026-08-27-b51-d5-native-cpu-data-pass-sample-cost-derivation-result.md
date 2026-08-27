# B51-D5：native CPU data-pass sample / cost 派生结果

日期：2026-08-27

类型：`REAL BLENDER 5.2 DOSE–RESPONSE DERIVATION`

判定：`EXACT_CPU_DATA_SAMPLE_REDUCTION_NOT_OBSERVED`

## 结论

在当前 exact data-pass 合同下，CPU data render 没有可证明的 sample-cost 降档。`TABLETOP_WIDE` 和 `INTERIOR_CHAIR` 的共同 `exactDataSampleFloor` 都是 `128 spp`：1、2、4、8、16、32、64 spp 中，没有一个剂量能在两种构图、两次重复上同时逐 float 复现冻结 128-spp CPU parent 的 Depth + 三层 Cryptomatte。

这直接改变 B51-H2 的成本假设。若 split path 仍要求 exact CPU data，它必须支付约一份完整 128-spp CPU render，再加一份 Metal beauty render 与合并开销；目前没有证据表明它比单份全 CPU production render 更便宜。

## 真实 Blender 矩阵

- Blender：本机 5.2.0 LTS，SHA-256 `60ba7a9b…b129f2`；
- CPU device：Apple M4 Max / `CPU`；固定四线程；
- 2 个冻结 H1 构图 × 8 个 sample dose × 2 个 fresh-process repeat；
- `32/32` Blender processes 和 renders 完成；
- 512×288、相同 seed offset、raw Cycles、七层 32-bit ZIP multipart EXR；
- 所有剂量的两个 repeat 在四个 data passes 上 exact，说明剂量内稳定；
- 两个 128-spp repeat 都逐 float 复现 H1 parent，说明 parent control 成立。

## 时间曲线

| Variant | 1 spp render / wall | 64 spp render / wall | 128 spp render / wall | 冻结 parent 128 spp |
|---|---:|---:|---:|---:|
| TABLETOP_WIDE | 0.038 / 0.779 s | 1.948 / 2.532 s | 3.454 / 4.032 s | 3.487 s render |
| INTERIOR_CHAIR | 0.050 / 0.623 s | 2.854 / 3.432 s | 5.217 / 5.808 s | 5.141 s render |

低 sample 的 raw render 确实快，1 spp 的 render operator 约快 91–103×；问题不是速度，而是 data semantics 与 128-spp parent 不同。32 个 fresh-process wall 总计 `55.421656 s`，render operator 总计 `36.616287 s`。

## 64 spp 仍然不是 exact data substitute

64 spp 是最接近 128 的低剂量，但差异仍广泛：

| Variant | Depth changed pixels | Crypto00 changed pixels | Crypto01 | Crypto02 |
|---|---:|---:|---:|---:|
| TABLETOP_WIDE | 93,278 / 147,456（63.26%） | 4,344（2.95%） | 3 | 0 |
| INTERIOR_CHAIR | 147,456 / 147,456（100%） | 4,143（2.81%） | 117 | 0 |

Cryptomatte ID floats 的巨大 absolute delta 不应被当成连续误差解释。Depth 的 `1e10` 背景 sentinel 也会使无条件 max-absolute 指标失真。D5 只回答 exactness；它没有把这些数值转化为抠像或深度合成质量结论。

## 审计

- base failure：`null`；
- attacks：`18/18`；
- independent audit：`PASS`；
- analyzer replay：byte-exact；
- frozen tools：`4/4` match；
- bound inputs：全部 match；
- rendered artifacts：`32/32` identity match；
- source `.blend` / parent EXR modified：`0`。

## 前置失败

正式 scientific matrix 前有两个零运行 preflight failure，均被独立保留：

1. 初始 spec 使用不存在的 OCIO 路径；C1 只改为 H1 已绑定的 config URI/SHA。
2. C1 retry 使用了错误 Blender binary SHA/bytes；C2 只改为 H1 已绑定且本机实测一致的 5.2 LTS identity。

两次失败均为零 Blender、零 render、零 EXR，不被追认为有效尝试。运行前还删除了约 397 MiB、可重建的项目 `.next/cache`，使未修改的 128 MiB write budget 重新满足 100 GiB reserve。

## 证据身份

- receipt SHA-256：`78627ca3038906af715ef6a110d8f14dff0d367d4c30c66e6f2e693786bf685e`；
- result SHA-256：`3fdeca2687388a87c84582baac03a07c0d63ca5233402739a4dcc2e53f65118e`；
- audit SHA-256：`bb95ae595d0514da1b3d57a87a4d402527984ad2bd6d54f4b191823156e9fe9d`；
- evidence-core SHA-256：`77e3b20dd1bfe8b1e185d9cefe91cbae5bd9516b54bf1a113d921a1b2e96fc88`；
- frozen tool commit：`3032206ae7537b733c4746c50ee61144b330f749`。

## 下一步

不能按原设想直接把 128-spp CPU data + Metal beauty 宣称为低成本 H2。下一项有证据支持的缺口是 B51-D6：为 Depth 分离 finite foreground、background sentinel 与遮挡边界误差；为 Cryptomatte 解码 ID/coverage 集并测量最终 matte，而不是比较编码 float 的绝对值。只有先冻结合成任务相关的安全指标，才能判断 16/32/64 spp 是否可能成为非-exact、但语义可接受的 CPU data profile。若 D6 也不支持降档，就应停止 split production 路径，把 Metal 限定为 preview/beauty-only。

Artifacts: `experiments/native-cpu-data-pass-sample-cost-derivation-v0-1/`, `specs/native-cpu-data-pass-sample-cost-derivation.v0.1.json`, `research/2026-08-27-b51-d5-native-cpu-data-pass-sample-cost-derivation-protocol.md`, `research/2026-08-27-b51-d5-c1-ocio-identity-correction-protocol.md`, `research/2026-08-27-b51-d5-c2-blender-identity-correction-protocol.md`, `blender/render_b51_native_cpu_data_sample_cost.py`, `scripts/run-b51-native-cpu-data-sample-cost.py`, `scripts/analyze-b51-native-cpu-data-sample-cost.py` and `scripts/audit-b51-native-cpu-data-sample-cost.py`.
