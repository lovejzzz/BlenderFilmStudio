# PC.0 attempt-01：启动前失败并保留

Date: 2026-08-31
Gate: `PC.0`
Verdict: `FAIL`

Formal runner 在创建 fresh evidence/work roots 后、任何 Blender process creation 之前停止，错误为：

`BFS_PC0_RUN_REJECTED Cannot access 'process' before initialization`

根因是 runner 函数内把子进程结果也命名为 `process`，遮蔽了 Node 的全局 `process`；因此前一行访问 `process.env` 时触发 JavaScript temporal dead zone。没有 Blender start、render、save、scene mutation、engine write、network/model call 或 mouse interaction。Frozen B62 source 与 accepted binary 的 SHA-256 均保持 exact。

Attempt-01 evidence/work roots永久保留。C1 correction ceiling 只允许把该局部结果变量及其直接引用重命名；probe、inventory scope、acceptance、resource ceiling 与 operation ceiling不得改变。修正后必须使用唯一 fresh attempt-02 roots，PC.0 audit PASS 前仍不得进入 PC.1。
