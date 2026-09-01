# PC5 C1：跨语言 self-hash 与 Blender 语义退出

Attempt-01 在任何场景、`.blend` 或 render 创建前失败。Frozen spec 由 JavaScript canonical JSON 产生；其中 `60.0` 按 JSON number 写为 `60`。Python builder 的 canonical JSON 保留 `60.0`，因此拒绝了相同语义的 spec。Blender 把 Python exception 写入 stderr 却返回 exit 0；base runner 只看进程退出码，错误地启动了不存在 `.blend` 的 reopen。独立失败审计为 13/13；attempt-01 work root 为空，网络、engine mutation、remote write 与 render 均为零。

C1 只修正执行可信度，不改变球、瓶子、物理参数、三镜头、60° 倾倒门槛、资源上限或视觉问题。Python self-hash 先把 integral float 规范为 JavaScript JSON number spelling。Runner 必须同时观察 exit 0、正确 success marker、预期 JSON artifact 存在且 stderr 无 Python traceback，才可开始下一进程。Attempt-02 使用唯一 fresh roots，attempt-01 保持不变。
