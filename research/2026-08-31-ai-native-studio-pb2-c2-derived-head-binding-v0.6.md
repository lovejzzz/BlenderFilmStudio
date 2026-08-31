# PB.2 C2：derived HEAD binding v0.6

C1 的 contract body 仍包含 `executionCommit`，所以仍是自引用。C2 完全移除该字段：contract 只绑定已知父提交；runner 从 Git 读取当前 HEAD，在确认 HEAD 包含 exact contract bytes 后，把 OID 写入 receipt；独立 auditor 再从 receipt OID 复算 parent 和 committed bytes。

这保持完整提交身份证明，同时消除所有 contract-body Git OID fixed point。B01/B02、八个负控、fresh roots、零 Blender/写入/网络上限与用户批准范围均不改变。
