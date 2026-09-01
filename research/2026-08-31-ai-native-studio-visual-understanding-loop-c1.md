# PC4-VU1 C1：fresh parent directory creation

PC4-VU1 attempt-01 在所有冻结输入、图片哈希、双编译和 19/19 合同测试通过后，首次尝试创建证据根时停止。运行器要求 `experiments/visual-understanding-loop/` 已存在，却使用了只创建最后一级目录的方式。终端返回 `ENOENT`。

停止发生在任何 evidence root、plan、receipt 或日志写入之前。`experiments/visual-understanding-loop/PC4-VU1-2026-08-31-attempt-01` 不存在；计数为 0 Blender start、0 render、0 scene mutation、0 network call、0 model call during compiler execution。

C1 只允许以下变更：

- 将冻结文件绑定升级到 v0.2；
- fresh root 的 `logs` 创建使用递归父目录创建；
- 正式根升级为 `PC4-VU1-2026-08-31-attempt-02`。

三份 schema、语义 treatment catalog、教学 packet、assessment、编译器核心、19 项测试及所有验收阈值保持字节不变。

