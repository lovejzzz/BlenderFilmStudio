# B62-T3-C2：controlled-failure receipt 引用的穷尽式修正

日期：2026-08-29

状态：PREREGISTERED — 修正前，v0.3 三棵 root 全部不存在

C1 tool freeze 成功越过 preflight，建立 manifest/ledger，并真实启动一个 Blender。Blender 读取 exact scene、打印 ready marker、被 SIGTERM，0 render；stdout/stderr 与 non-promotable failed receipt 都已耐久写入。runner 随后在生成 `STAGE_FAILED` event 时再次读取不存在的 `failed.path`，因此 v0.2 在 0 formal render 处失效。

这是 C1 同类 bug 的第二个调用点。C2 在修改前枚举所有 helper-return 属性：`writeExclusiveDurableHashed` 的无效 `.path` 只剩两处，且都引用同一个 failed receipt；`writeStageReceipt` 与 `createManifest` 确实返回 path，不改。授权实现显式 `failedReceiptPath`，同时切 fresh v0.3，并把 v0.1/C1 与 v0.2/C2 失败链全部纳入准入与最终审计。

不改变任何 Cycles、EXR、288 帧、restart、receipt、24 gates/attacks、资源或人审边界。
