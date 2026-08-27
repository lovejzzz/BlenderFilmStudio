# B51-D4：split-backend multipart EXR 合并负结果

日期：2026-08-27

类型：`ZERO-RERENDER ENGINEERING DERIVATION`

判定：`NATIVE_SPLIT_BACKEND_ASSEMBLY_DERIVATION_INVALID`

## 先说结论

Metal beauty / CPU data 的七层 multipart EXR 可以被正确组装：四份输出的 roster、provenance、finite gate 与逐 pass float array 全部通过。它尚不能晋级，因为冻结合同同时要求两次合并文件 byte-exact；`TABLETOP_WIDE` 两份容器只差七个字节，但 SHA-256 不同。独立重放也只有 receipt 为 byte-exact，正式 audit 因而是 `FAIL`。

差异已定位为 OpenImageIO 自动注入的 `capDate` 秒值，而不是像素或 pass 选择错误。第一份 TABLETOP 输出写入 `2026:08:27 04:08:47`，第二份写入 `04:08:48`；七个 subimage header 各变一个 ASCII 字节。随后同一秒完成的两份 `INTERIOR_CHAIR` 输出 byte-exact。这是对根因的事后诊断，不是对无效结果的重新标记。

## 前置失败也被保留

1. 第一冻结工具把完整 preregistration SHA 写错为不存在的对象，在创建输出根之前 fail closed；C1 只修正该 literal。
2. C1 工具随后在磁盘准入门停止：`df -h` 仅显示 `99 GiB` 可用，低于“预计写入后保留 100 GiB”的冻结要求。没有 receipt 或 EXR 被写入。
3. 按用户先前授权，只删除约 1.6 GiB、可重新下载的 Playwright browser cache。重试前可用空间为 `108197478400` bytes；正式 receipt 独立测得 `108197388288` bytes，并通过未修改的容量门。

两次 preflight failure 分别保存在：

- `experiments/native-split-backend-assembly-derivation-preflight-failure-v0-1/failure.json`
- `experiments/native-split-backend-assembly-derivation-capacity-failure-v0-1/failure.json`

## 正式结果

- Blender processes：`0`；renders：`0`；source EXRs modified：`0`；
- 读取：四份冻结的 B51-H1 Blender 5.2 multipart EXR；
- 写入：两组 × 两个 merge replicate，共四份七层 multipart EXR；
- 四份输出的 selected pass float arrays：全部 exact；
- 四份输出的 pass roster / provenance / finite gates：全部通过；
- `TABLETOP_WIDE` merge replicate：不同 SHA，文件大小同为 `3224940` bytes，且只差七个 `capDate` 字节；
- `INTERIOR_CHAIR` merge replicate：byte-exact，SHA-256 `2f58751d067d4b8429ef719d4f1b78c60df263899848702afdd4a493fa0f1f3c`；
- base failure：`MERGE_REPLICATE_BYTE_IDENTITY`；
- attacks：`13/15`。A14/A15 被既有 base failure 优先遮蔽，未达到各自预期 reason；
- independent audit：`FAIL`；frozen tools `2/2` match；artifact replay `1/6` byte-exact。

## 根因证据与窄修正方向

OpenImageIO 的官方 OpenEXR writer 源码说明：如果 client 未提供 `DateTime`，writer 会读取当前本地时间并自动设置它；OpenEXR 映射表将 OIIO 的 `DateTime` 写成 header 的 `capDate`。本工具复制的 Blender spec 有自定义 `Date`，但没有 `DateTime`，因此每次 writer open 都注入 wall-clock metadata。[OpenImageIO OpenEXR writer source](https://github.com/AcademySoftwareFoundation/OpenImageIO/blob/main/src/openexr.imageio/exroutput.cpp) · [OpenImageIO metadata mapping](https://openimageio.readthedocs.io/_/downloads/en/v2.5.6.0/pdf/)

下一次 correction 只能把每组 Metal beauty source 的冻结 `Date` 规范化为 OpenEXR `DateTime`，并在七个输出 spec 上显式写入；同时增加 `capDate` 一致性 gate。不能改变像素、pass routing、输入、压缩、阈值、攻击或审计原则。

## 证据身份

- receipt SHA-256：`9923400ea376706e44b9dc3e79aff91882e2e5393903c679dbb2e36d8ce8f1a6`；
- result SHA-256：`56587ea8b77378dd2fa4b44fec0788795f96c3b3fed1f2af2921014bd077e37e`；
- audit SHA-256：`19e2d0ac14e9fbc3360dac06a64aae017e3dfb960bbf8ed4ca14bc8337288ec1`；
- evidence-core SHA-256：`4986ed90d85889d00903cbeb8b7238cdba7907c2261da098d38caea181e9ff5f`；
- tool/evidence freeze HEAD：`8cd3db4a814832e18b9e9460949bdfe1bb630eac`。

## 不能声称什么

这批输出不能支持 deterministic assembly、split-backend production、H2 holdout、Metal beauty 晋级或长序列稳定性。像素 exact 只说明 routing 实现本身在这四份产物上正确；容器级复现合同仍然失败。

Artifacts: `experiments/native-split-backend-assembly-derivation-v0-1/`, `specs/native-split-backend-assembly-derivation.v0.1.json`, `scripts/run-b51-native-split-backend-assembly-derivation.py`, `scripts/audit-b51-native-split-backend-assembly-derivation.py`, `research/2026-08-27-b51-d4-c1-preregistration-sha-correction-protocol.md` and `research/2026-08-27-b51-d4-c2-capacity-readmission-protocol.md`.
