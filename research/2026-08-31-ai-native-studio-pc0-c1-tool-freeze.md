# PC.0 C1：最小启动器修正与 attempt-02 freeze

Date: 2026-08-31
Gate: `PC.0`
Status: `FROZEN_BEFORE_PC0_START`

Attempt-01 已作为0-start harness failure封存。C1 唯一 semantic logic correction 是把 runner 内的子进程结果局部变量从 `process` 改名为 `execution`，并同步其直接引用，解除对 Node global `process.env` 的 temporal-dead-zone 遮蔽。为保持失败证据和路径不被复用，versioned runner/auditor仅另行绑定 C1 freeze 与唯一 fresh attempt-02 evidence/work roots。

Probe、inventory scope、source/binary、acceptance、operation/resource ceilings全部不变。Static Python AST、Node syntax、forbidden probe patterns与synthetic 14/14保持PASS；attempt-02 roots在freeze时均不存在。Formal attempt仍最多1 Blender start，0 render/save/engine/network/model/mouse；independent audit PASS前不得进入PC.1。
