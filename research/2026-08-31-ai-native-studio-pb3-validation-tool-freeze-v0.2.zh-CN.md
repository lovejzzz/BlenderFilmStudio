# PB.3 validation tool freeze v0.2

状态：**STATIC TOOL AUDIT PASS；FORMAL EXECUTION 未授权**

PB.3 的 combined oracle 已冻结为每个 benchmark 两个 zero-render stage：

1. `build`：inspect typed proposal/approval，只写一次 approved BuildPlan，构建一次
   semantic scene，把 Project/Scene/Shot/Character exact mapping 写入 workspace，做
   background Expert-state 往返并保存；
2. `reopen`：重新打开该 `.blend`，复核 canonical/semantic/provenance identity、
   typed workspace persistence，再做一次 lossless Expert-state 往返。

B01/B02 合计上限因此为 4 次 Blender start、2 次 proposal execution、2 次
BuildPlan write、2 次 scene build、2 次 workspace save、2 次 reopen；render、
network、engine source edit 和 engine remote write 都冻结为 0。B01/B02 没有 actors，
Character 使用 exact sentinel `NONE / No Character`。

runner 没有 `--execute` 会拒绝；即使带 `--execute`，非授权 v0.3 template 也会在
创建 roots 前拒绝。正式 execution contract 必须显式命名 PB.3、绑定 exact tool
freeze、只写 parent commit 并由 runner 从 committed HEAD 派生 execution OID。

独立 static auditor 检查 runner/probe/compiler/formal auditor hashes、AST network
imports、offline/disable-autoexec argv、exclusive writes、binary/source identity、
self-test 和 inert invocation，共 28/28 PASS，self hash
`db8e287f59b55fa741970422277b7588aa6533972fda31116da8e40a901079bb`。
过程中 formal roots、Blender start、proposal execution、BuildPlan write、scene
mutation、render、engine write 和 network call 全部为 0。

本结果只证明工具被冻结且保持惰性，不是 PB.3 PASS。准确授权范围已写入
`specs/ai-native-studio-pb3-validation-only-authorization-request.v0.2.json`；在
显式 PB.3 授权前不得创建正式 execution contract 或运行 formal attempt。
