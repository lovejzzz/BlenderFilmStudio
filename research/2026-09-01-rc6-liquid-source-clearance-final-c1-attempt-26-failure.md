# RC6 最终分辨率静态确认 C1 attempt-26 失败

`RC6-2026-09-01-source-clearance-final-c1-attempt-26` 保留为 `FAIL_EXECUTION`。Blender 启动一次，在约 `0.36 s` 内于任何 Mantaflow bake、保存或渲染之前停止。

C1 正确等待 identity-before-placement wrapper 完成第一层组合，但此时 `source` 仍是 source-clearance wrapper，而不是包含 resolution assertion 的最终场景源码。因而 resolution 唯一替换仍为零并 fail closed。

C2 必须把最终分辨率替换代码注入 source-clearance wrapper 的末端执行锚点，使替换发生在该 wrapper 已把 local-domain、signed-component、source-clearance 和 identity-order 变换全部应用到最终场景源码之后。C2 在提交和 Blender 启动前，必须先由普通 Python 组装预检到达预期的 `bpy` 导入边界；不得再以 Blender 启动作为包装器语法/层级测试。
