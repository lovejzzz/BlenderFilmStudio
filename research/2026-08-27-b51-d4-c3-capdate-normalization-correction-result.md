# B51-D4-C3：deterministic `capDate` 修正结果

日期：2026-08-27

类型：`ZERO-RERENDER CORRECTION + INDEPENDENT REPLAY`

判定：`NATIVE_SPLIT_BACKEND_ASSEMBLY_CAPDATE_CORRECTION_USABLE`

## 结论

D4 的七字节非确定性已被单点关闭。C3 从每组冻结 Metal beauty source 的 `Date` 派生 OpenEXR `DateTime`，在七个 output subimage 上显式写入。两组 merge replicate 现在都达到文件级 byte-exact；独立审计重放 receipt、result 和四份 EXR，`6/6` byte-exact。

这证明该合并器可在两组已知 H1 输入上稳定生产“Metal Combined/Normal/Vector + CPU Depth/Cryptomatte”的七层 multipart EXR。它不证明新画面上的 split-backend production 合同；B51-H2 仍须使用预注册的 unseen renders。

## 冻结修正是否按预期发生

| Pair | Metal source `Date` | 写入七层的 `DateTime` | 两次合并 SHA-256 | Byte-exact |
|---|---|---|---|---|
| TABLETOP_WIDE | `2026/08/27 03:18:33` | `2026:08:27 03:18:33` | `8157aab6…729de9` | yes |
| INTERIOR_CHAIR | `2026/08/27 03:18:40` | `2026:08:27 03:18:40` | `cbd80be0…cf9cc` | yes |

每份输出重新打开后，7/7 subimage 的 `DateTime` 均与对应派生值一致。没有删除 metadata，也没有使用新的当前时间或人工常量。

## 原有合同保持不变

- Blender processes：`0`；renders：`0`；source EXRs modified：`0`；
- 四份 source EXR 与全部 parent evidence 精确匹配；
- Metal：Combined / Normal / Vector；CPU：Depth / CryptoObject00–02；
- 四份输出的 selected pass arrays 全部 float-exact；
- roster、geometry、common metadata、Cryptomatte manifest、provenance、finite gates 全部通过；
- 100 GiB reserve gate 通过：正式测量可用 `108060344320` bytes，预计写入后 `107993235456` bytes；
- 原始 attacks `15/15`，correction attacks `4/4`；总计 `19/19`；
- base failure：`null`；correction failure：`null`。

## 独立审计

Audit status：`PASS`。冻结 assembler/auditor 两个 Git blob 均匹配 receipt。独立临时目录重放得到：

- receipt：byte-exact；
- result：byte-exact；
- TABLETOP R1/R2：byte-exact；
- INTERIOR_CHAIR R1/R2：byte-exact。

## 证据身份

- receipt SHA-256：`d31a5bd8e44a1d80035b2fdc8f22dbde777e60d0cf4e82f870bedc29ede4af76`；
- result SHA-256：`aa231952119cf91e0d252a0e8b08aa1f72ac1e49f24fd82844aabafba9e81cfb`；
- audit SHA-256：`864f257fdb9f14c7a3f217cb4e62fc21b4947896119ba59c9562c113b48ca84e`；
- evidence-core SHA-256：`6a28c29ece33ffff12f537f4220a3a8bafb80c5192d14e19a2d46972d42379cd`；
- frozen tool commit：`0e9e55aa90014b4ca4ceee448a375bcde8c02c62`。

## 不能声称什么

C3 不追认无效 D4，不测试 Blender rendering、不测试 unseen composition、不晋级 Metal beauty、不证明总 wall-cost 优势，也不证明动画时序、长序列、跨主机或跨 OIIO 版本稳定。

## 下一步

预注册 B51-H2 unseen split-backend holdout。至少应包含：新的场景/帧；每个 cell 的 CPU data 与 Metal beauty 独立 render receipt；canary；跨后端相机/几何身份；C3 merger；合并后 exact pass-source gate；完整 wall cost（两个 render + merge）；同输入 clean replicate；对照全 CPU production artifact。未通过时保留 CPU production passes，并把 Metal 限定为 preview/beauty candidate。

Artifacts: `experiments/native-split-backend-assembly-capdate-correction-v0-1/`, `specs/native-split-backend-assembly-capdate-correction.v0.1.json`, `research/2026-08-27-b51-d4-c3-capdate-normalization-correction-protocol.md`, `scripts/run-b51-native-split-backend-assembly-derivation.py` and `scripts/audit-b51-native-split-backend-assembly-derivation.py`.
