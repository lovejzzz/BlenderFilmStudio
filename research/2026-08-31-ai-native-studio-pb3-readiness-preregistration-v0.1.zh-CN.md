# PB.3 readiness preregistration v0.1

状态：**READINESS PREREGISTERED；PB.3 FORMAL EXECUTION 未授权**

PB.3 要求把四件事放在同一个可审计结果里：B01/B02 approved compile 的
canonical-exact BuildPlan、semantic/provenance identity、可持久化的
Project/Scene/Shot/Character 状态，以及 lossless Expert Mode 往返。

只读盘点确认：

- PB.2 已证明两个 proposal/approval 可安全 inspection，但未执行 proposal、未写 BuildPlan；
- F0.4 已分别证明 B01/B02 exact BuildPlan 与 semantic identity；
- F0.3 已分别证明 typed workspace 持久化和 Expert Mode 往返；
- 当前 `film-engine` source 同时包含 `film_studio_contract.py` 与
  `film_studio_workspace.py` contract bridge，HEAD clean 且仍为 `4061e12b…`；
- 尚无 accepted run 在 PB.1 accepted binary 上把上述四项组合在一起。

因此本次只冻结 inputs、哈希和 missing proof。没有创建 PB.3 formal root，
Blender start、proposal execution、BuildPlan write、scene mutation、render、
engine source/remote write 与 network call 全部为 0。

下一版 formal protocol 必须先固定 fresh roots、retained binary、进程计数、
两份 exact plan/semantic identity、workspace mapping/persistence oracle、Expert
Mode oracle、所有 pre-write negative controls、资源上限和独立 auditor。
在此之前不得把本 readiness inventory 描述成 PB.3 PASS，也不得启动 PB.4。
