# RC6 最终分辨率 mesh-only C1 attempt-29 失败

`RC6-2026-09-01-final-mesh-only-c1-attempt-29` 保留为 `FAIL_EXECUTION`。第一个 formal Blender start 在任何 `free_mesh`、`bake_mesh`、保存或渲染前停止；fluid data bake 与 mesh bake 均为零。

## 原因

C1 已经正确把复制场景的 cache_directory 绑定到 candidate absolute cache root。随后 frozen setting 检查将 Blender RNA 中读取出的单精度 `particle_radius=1.600000023841858` 与十进制输入 `1.6` 用 `1e-12` 比较，实际差值约为 `2.3842e-8`，因此把正常的 float32 往返误判为配置变化。

这不是物理模拟失败，也不是机器性能问题；它是验证工具的数值表示契约错误。

一次 post-failure 只读 Blender 诊断确认：`particle_number=2`、`resolution_max=192`、frame range `1..7` 与 baked flags 均正确。诊断后，candidate 的 14 个 config/data 文件、21 文件完整 cache 与 retained 输入完全相同，retained work-manifest 文件也保持 exact。

## C2 规则

C2 只允许把 frozen `particle_radius` 的读取比较容差从 `1e-12` 修正为 `1e-6`，覆盖 Blender RNA float32 的正常往返误差；不得修改 cache rebind、四个 cell、任何物理参数、接受阈值、资源上限或计数。

必须使用 fresh attempt-30 roots；不得继续使用或修补 attempt-29。
