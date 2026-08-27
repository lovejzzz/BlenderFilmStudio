# B51-D3：CPU–Metal pass 与空间差异定位结果

日期：2026-08-27

类型：`ZERO-RERENDER DERIVATION`

判定：`METAL_PASS_LOCALIZATION_USABLE`

## 先说结论

B51-H1 的失败不能被归结成一种统一的“边缘误差”。Cryptomatte 的 CPU–Metal 非 exact 像素确实全部落在预冻结的对象边界邻域内；Depth 则在四个构图中只有 `3.754%–80.241%` 的变更像素落在该邻域，大量微小差异覆盖物体内部。`INTERIOR_CHAIR` 的 Combined 高误差虽然不是稀疏单点，但其全部 squared-error energy 都落在 Depth/Cryptomatte disagreement 的两像素膨胀区内。

因此，证据支持“beauty outlier 与 data-pass disagreement 空间相关”，不支持“所有 data-pass 差异只是边缘噪声”。最保守的下一候选是分离生产合同：Metal 生成 beauty，CPU 生成 Depth/Cryptomatte；该候选仍需新的预注册 holdout 验证跨后端空间配准、成本与完整 pass 语义，不能由本次定位直接晋级。

## 冻结边界与输入

- 不启动 Blender，不产生新 render，不修改任何 H1 EXR；
- 只读取 H1 corrected receipt、corrected result、corrected audit 与 12 份正式 EXR；
- 12/12 EXR 重新匹配 receipt 的 SHA-256、字节数、512×288 尺寸、七层 subimage roster 与有限值；
- Depth 边界、Cryptomatte 边界、像素膨胀半径、beauty 高误差阈值和关联门槛全部在分析器实现前写入 spec；
- 可用空间约 `107.44 GB`，在预留 100 GiB 后仍通过 16 MiB 写入预算。

## Cryptomatte：稀疏且 100% 边界定位

四个构图、两个 Metal repeat 的每个 Cryptomatte pass 都达到冻结的 `≥95%` boundary-localized 分类；实际 near-boundary fraction 全部为 `1.0`。活动层的变更规模很小：

| 构图 | 活动 Crypto 变更像素 | 图像占比 | 边界邻域占比 |
|---|---:|---:|---:|
| TABLETOP_WIDE | 4 | 0.0027% | 100% |
| TABLETOP_TIGHT | 8 | 0.0054% | 100% |
| INTERIOR_CHAIR | 123 + 13 | 0.0834% + 0.0088% | 100% |
| INTERIOR_WINDOW | 14 + 1 | 0.0095% + 0.0007% | 100% |

Cryptomatte float 是 ID/coverage 编码，极大的数值绝对差没有普通连续量的物理意义。本实验只证明变更位置与边界的关系，没有证明 ID 集合、coverage 合成或抠像结果语义等价。

## Depth：广泛的低幅非 exact

Depth 的 changed-pixel fraction 为 `33.51%–80.19%`，但单个 interior maximum absolute difference 只有约 `3.34e−6–4.77e−6`。它不是高幅局部跳变，而是广泛、低幅、跨后端浮点差异：

| 构图 | Depth 变更像素 | 图像占比 | 边界邻域占比 | interior max abs diff |
|---|---:|---:|---:|---:|
| TABLETOP_WIDE | 49,418 | 33.51% | 6.06% | 4.768e−6 |
| TABLETOP_TIGHT | 70,351 | 47.71% | 3.75% | 4.768e−6 |
| INTERIOR_CHAIR | 102,750 | 69.68% | 21.37% | 3.338e−6 |
| INTERIOR_WINDOW | 118,248 | 80.19% | 80.24% | 3.338e−6 |

所以不能把 Depth exact failure 全部解释成轮廓 coverage。它也不等于 Depth 在合成上必然不可用；那需要按米制深度误差、镜头空间、遮挡边界和具体合成算子另立安全门。

## Chair beauty outlier：与 data disagreement 强相关

`INTERIOR_CHAIR / CPU_R1 ↔ METAL_R1` 有 1,971 个像素的 max-channel absolute error 超过 `1e−3`，形成 829 个四连通组件，最大组件 179 像素；最大通道误差 `0.347776`。误差分布具有重尾：P95 仅 `1.788e−7`，P99 为 `0.001455`，P99.99 达 `0.209555`。

冻结的关联规则把 Depth/Cryptomatte disagreement union 膨胀两像素。本对照的 Combined squared-error energy 总计 `6.236593`，其中 `6.236593` 落在该 mask，关联比例 `1.000000`，通过 `≥0.90` 的关联分类。这是空间关联，不是因果证明；它没有区分几何交点、着色法线、采样路径或设备数学实现中的具体来源。

## 审计与证据

- 独立审计：`PASS`；
- adversarial attacks：`11/11`；
- receipt、result 与 5 张 PNG：`7/7` byte-exact replay；
- Blender processes：`0`；renders：`0`；source EXRs modified：`0`；
- evidence-core SHA-256：`9fc4b2a3174758d8de9bf9a987813ac4708333bf53c5a84ccb04a91374350c82`；
- receipt SHA-256：`cfa077f950985f0ab7024d32c666631e27e7e3d5c57aa5645e5f1506a6f86d2a`；
- result SHA-256：`10dc769383e88db5bfad75f95ad882a18758e9b7a6db1c3a683a46eed98bfec0`；
- audit SHA-256：`9911a59b627aaa511626583315c10a98df3a39f9de589e519345f71e87a9c458`。

## 不能声称什么

本实验不晋级生产后端，不证明人眼不可见、Cryptomatte 语义等价、Depth 合成安全、差异根因、长序列稳定或跨机器泛化。五张 PNG 是按冻结映射生成的诊断载体，不是感知质量评分。

## 下一步

预注册 B51-H2 split-backend holdout：同一冻结场景分别用 Metal 输出 Combined/Normal/Vector beauty 域、CPU 输出 Depth/Cryptomatte data 域，并验证相同相机/几何的跨后端像素配准、合并后的 multipart EXR roster/metadata、两次净构建复现、总 wall time 与攻击面。若混合产物不能在不篡改语义的情况下通过，则保留全 CPU production-pass 路径，并把 Metal 限定为 preview 或 beauty-only candidate。

Artifacts: `specs/native-metal-pass-localization.v0.1.json`, `experiments/native-metal-pass-localization-v0-1/`, `scripts/analyze-b51-native-metal-pass-localization.py`, `scripts/audit-b51-native-metal-pass-localization.py` and `research/2026-08-27-b51-d3-native-metal-pass-localization-protocol.md`.
