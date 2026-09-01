# RC6 最终分辨率 mesh-only C2 attempt-30 结果

`RC6-2026-09-01-final-mesh-only-c2-attempt-30` 的执行为 `PASS_EXECUTION`，独立审计为 `PASS 21/21`，科学结论为 `FAIL_FINAL_STATIC`。因此不得解锁 slow solver-owned tip。

## Pipeline 结论

- 4 次 Blender start；
- 4 次 fluid mesh bake；
- **0 次 fluid data bake**；
- 0 次 render、network call 或 engine remote write；
- 四组 Blender wall time 分别约 61.12、82.39、109.20、109.91 秒；
- 全矩阵约 6 分钟，而不是把约 24 分钟的七帧 resolution-192 data solve 重复四次。

这证明 copied immutable data cache + explicit absolute cache rebind 可以把“物理数据求解”和“液面重建参数选择”分离。M2 Max 在运行时使用约 11 个 CPU 核；前 10 帧约 32 分钟与 retained resolution-192 solve 的速度一致，不是主机异常，但该 final tier 不适合作为交互验证默认档。

## 科学结果

| mesh radius | source volume error | temporal drift | outside cup + 1 voxel | 结论 |
|---:|---:|---:|---:|---|
| 8.0 | 13.81% | 1.86% | 1.07% | 体积与边界均未过门 |
| 9.0 | 4.40% | 1.55% | 7.68% | 体积通过、边界失败 |
| 9.5 | 2.07% | 1.34% | 10.47% | 体积通过、边界失败 |
| 10.0 | 7.75% | 1.37% | 10.82% | 体积与边界均失败 |

四组 non-manifold edge 均为零，temporal drift 均在 5% 门内。更大的 reconstruction radius 可以补回总体积，却同时把表面推过杯内边界，形成明确的体积—containment 冲突。不得通过放宽 1% containment 阈值或只选择体积最好值来宣称通过。

## 下一步边界

下一次只允许研究液面重建阶段的一个可解释变量，并继续复用 exact retained data cache。优先验证 Blender liquid mesh 的 smoothing/concavity 参数能否在不重算物理、不过度扩张边界的情况下改善闭合表面；必须先冻结单变量小矩阵与同一组五项科学阈值。
