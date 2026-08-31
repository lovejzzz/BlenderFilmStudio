# PB.3 validation-only C3 corrected tool freeze v0.8

日期：2026-08-31
状态：`PASS_STATIC_32_OF_32_INERT`
Attempt-02 roots：不存在
Blender start / proposal execution / BuildPlan write / render：`0 / 0 / 0 / 0`

## 结论

C3 为 retained attempt-01 的唯一根因提供了可执行但仍 inert 的校正路径。Corrected tool contract 与 v0.2 做结构化递归比较后只有一个 JSON leaf 不同：

`commonInputs[0].sha256`

- from：`b308c7832d4f4b02e16f930f19dcf1baae7475d2f283aee3cb453f05a2224a`
- to：`b308c7832d4f4b02e16f930f19dcf1baaeae7475d2f283aee3cb453f05a2224a`

13 个 common/fixture input 在 corrected contract 下全部 exact。Source、fixture bytes、combined oracle、四次 start 上限、2 GiB / 64 MiB ceilings、zero-render/network/engine-write 权限边界均未改变。

## Consolidated runner

C3 runner 直接复用冻结 base runner，而不是通过临时 corrected files 绕过 C1/C2：

- 在 root 创建前验证 corrected tool、13/13 inputs、逐字 authorization、single-path execution commit 和 exact authorized roots；
- 验证 request、C3 tooling contract、corrected tool exact bytes 已存在于 execution parent；
- 在运行前后复算 retained attempt-01 work/evidence manifests；
- 四个 Blender process 仍串行、offline、disable-autoexec，stdout/stderr 使用 exclusive-create；
- PASS receipt 前复算 work/evidence manifests、projected receipt bytes 和 unchanged ceilings；
- PASS 后重建四组 argv 并读取八份实际日志做 SHA-256 比对。

## Independent auditor

C3 auditor 先运行冻结 base semantic auditor，复核 probes、BuildPlans、semantic structures 与 no-render evidence；随后独立验证：

- corrected tool / C3 / exact authorization bindings；
- execution commit 单路径与 parent-frozen bytes；
- exact work/evidence/source/binary arguments；
- 四组 argv、八份日志；
- receipt 前、base audit 后与 final C3 audit 后的 manifests/byte ceilings；
- retained attempt-01 manifests 完全不变。

## 冻结产物

- corrected tool：`specs/ai-native-studio-pb3-validation-tool-freeze-c3-corrected.v0.8.json`
  - SHA-256：`b86b5de659ebf09761ea8a74bd252d4d11c66073fd50a17680ebb50debf4558d`
- C3 execution tooling：`specs/ai-native-studio-pb3-validation-c3-execution-tool-freeze.v0.8.json`
  - SHA-256：`2711b7fd7f5cc4cc026978921414e35554fc2dab077448fad3e9ca00ba3f1724`
- runner：`scripts/run-ai-native-studio-pb3-validation-c3.py`
  - SHA-256：`80fafdc044f149d08b0d03fe71b4037e461bd88066a5c5ca2be5e4a8a50df76e`
- independent auditor：`scripts/audit-ai-native-studio-pb3-validation-c3.py`
  - SHA-256：`aef6338f574cf0e394594d20f9d7e68a37b15e5216d672328f78db68b2f53c2a`
- static auditor：`scripts/audit-ai-native-studio-pb3-tool-freeze-c3.py`
  - SHA-256：`b2bb3db7b7e771c217718c2522a8bdba12dbdec64c56c1e85ab920129043534e`
- inert template：`specs/ai-native-studio-pb3-validation-execution-c3-template.v0.9.json`
  - SHA-256：`b21d57cd64a825ebcdb40af53b7fd29e4c4d51f8198a8764abd6ac5467ea24ed`
- authorization request：`specs/ai-native-studio-pb3-validation-only-authorization-request-c3.v0.8.json`
  - SHA-256：`184e30445e917c00e6a07ee9c4cfde9f6c4b0c17db3a774098d8aa571693e252`
- static audit：`experiments/ai-native-studio-phase-b/PB.3-c3-tool-freeze-2026-08-31-mac-m2max-attempt-01/audit.json`
  - verdict：`PASS 32/32`
  - file SHA-256：`6afd9e4849fe2b9511a6051c341b8f4304e13fc382c58a041183f4d1a85dfd8e`
  - self hash：`983d315310c6198dbba0feaaa3109983db7e2d37a0b36775390a3bf037bcd0cf`

额外纯函数负控证明 runner/auditor 的 B01/B02 build/reopen argv 完全一致，且两者都拒绝 root symlink 与 descendant symlink。

## 权限边界

Static audit 执行一次 self-test 与一次 inert template rejection，未创建 attempt-02 roots，也未启动 Blender。Attempt-01 仍 immutable。Attempt-02 必须先逐字批准 `specs/ai-native-studio-pb3-validation-only-authorization-request-c3.v0.8.json`，然后用单路径 commit 新建 execution contract；一般性 permission 不能替代该边界。PB.4–PB.7 继续未授权。
