# PB.3 validation-only C1：资源上限执行校正 v0.3

日期：2026-08-31
状态：`PASS_STATIC_25_OF_25_INERT`
正式 PB.3 work/evidence roots：不存在
Blender start / proposal execution / BuildPlan write / render：`0 / 0 / 0 / 0`

## 结论

PB.3 v0.2 工具冻结保留为有效的 combined-oracle 设计与 28/28 静态证据，但在完成性复核中发现一个正式执行前必须修正的工具缺口：合同声明了 work root 2 GiB、evidence root 64 MiB 的容量上限，runner 没有实际执行这些上限，独立 auditor 也没有重新计算它们。

C1 不改变 B01/B02、canonical/semantic/provenance oracle、四次 Blender start 上限或任何权限边界。它只增加以下 fail-closed 约束：

- 四组 Blender stdout/stderr 日志必须使用 exclusive-create；
- work/evidence root 下出现 symlink 即拒绝；
- runner 在写 PASS receipt 前计算 work bytes、已有 evidence bytes、最终 receipt bytes 和 projected final evidence bytes；
- work root 超过 `2,147,483,648` bytes 或 evidence root 超过 `67,108,864` bytes 时停止；
- independent auditor 独立重算两个 root 的 regular-file bytes、receipt projection，并在写 audit 前计算自己的 projected bytes。

## 冻结产物

- 基础工具合同：`specs/ai-native-studio-pb3-validation-tool-freeze.v0.2.json`
  - SHA-256：`52e2dda7a6d0846ad1ed2c89d466b4b848165cb38763621d17cbf08bc583009a`
- C1 correction：`specs/ai-native-studio-pb3-validation-tool-c1-resource-enforcement.v0.3.json`
  - SHA-256：`b7b4c77009ccaf7dfa17efd9fa9559cbc402b25f91f9cc9af1bd5e0e4ca4a1c0`
- C1 runner wrapper：`scripts/run-ai-native-studio-pb3-validation-c1.py`
  - SHA-256：`4261866539a404766027fbe1fe737686857529f811a03bd8691db008e35b133a`
- C1 independent auditor wrapper：`scripts/audit-ai-native-studio-pb3-validation-c1.py`
  - SHA-256：`ccbfaa084499985ef1e25411b239f0ddb21d2c79cfcdc4bc8b8e197e67c66556`
- C1 static auditor：`scripts/audit-ai-native-studio-pb3-tool-freeze-c1.py`
  - SHA-256：`cd20a1e2ca4923a3172cf03b06f43d1cfa8195da7ec70a49e2a74a0b8b6ee271`
- 非可执行 execution template：`specs/ai-native-studio-pb3-validation-execution-c1-template.v0.4.json`
  - SHA-256：`2d0447d025a7c7a2d7a619a61734c9c86dc7140318f364e3bf6e7cbe64f18abb`
- 静态审计：`experiments/ai-native-studio-phase-b/PB.3-c1-tool-freeze-2026-08-31-mac-m2max-attempt-01/audit.json`
  - 文件 SHA-256：`2ce3741249e6d9ad1627f0c6b80274302f66cfeef4b96c46dd17a64aacade09d`
  - audit self hash：`1eecc7dd22dc4af4bd5196294ab81b99604334c38e33c43c1e1c146e30683b05`
  - verdict：`PASS 25/25`

## 权限边界

C1 静态冻结没有启动 Blender、没有执行 proposal、没有写 BuildPlan，也没有创建正式 PB.3 root。v0.4 template 的 authorization 字段仍为 null，不能被模板文件、一般性的“继续”或更早 PB.2 授权替代。

未来一次正式执行必须先取得并提交
`specs/ai-native-studio-pb3-validation-only-authorization-request-c1.v0.3.json`
所列的 exact PB.3 C1 authorization，再生成新的不可变 execution contract。PB.4–PB.7、film-engine source/ref/tag/release mutation、network、render、签名、公证和 DMG 继续为零权限。
