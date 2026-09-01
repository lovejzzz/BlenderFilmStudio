# RC6 最终分辨率 mesh-only attempt-28 失败

`RC6-2026-09-01-final-mesh-only-attempt-28` 保留为 `FAIL_EXECUTION`。第一个 formal Blender start 在任何 `free_mesh`、`bake_mesh`、保存或渲染前停止；fluid data bake 与 mesh bake 均为零。

## 原因

复制的 `baked-state.blend` 内保存的 cache_directory 为：

`//../../RC6-2026-09-01-feasibility-attempt-13/mantaflow-cache`

它在 candidate blend 中仍解析到旧 feasibility root，而不是 candidate 旁边的完整缓存副本。scene tool 的 exact-root 检查正确阻止了后续 free/bake。

两次 post-failure 只读 Blender 诊断分别验证：

1. 当前 blend 路径正确，但原始 cache_directory 解析到旧 root；
2. 在内存中把 cache_directory 显式设为 candidate 绝对路径后，`has_cache_baked_data=true` 与 `has_cache_baked_mesh=true` 保持不变。

诊断后，candidate 的 14 个 config/data 文件与 retained data manifest 完全相同，candidate 的 21 文件完整缓存与初始副本相同，retained attempt-27 work manifest 也完全相同。

## C1 规则

C1 必须在任何 cache flag 判断、`free_mesh` 或 `bake_mesh` 之前显式把复制场景的 cache_directory 绑定到 candidate absolute cache root，并再次核对：

- resolved cache root exact；
- data/mesh baked flags 仍为 true；
- 14 个 config/data 文件哈希 exact；
- 初始 21 文件 roster exact。

必须使用 fresh attempt-29 roots；不得继续使用或修补 attempt-28。
