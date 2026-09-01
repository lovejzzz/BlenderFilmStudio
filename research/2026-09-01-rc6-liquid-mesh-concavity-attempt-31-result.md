# RC6 液面 concavity attempt-31 结果

`RC6-2026-09-01-mesh-concavity-attempt-31` 的执行为 `PASS_EXECUTION`，独立审计为 `PASS 21/21`，科学结论为 `FAIL_FINAL_STATIC`。slow solver-owned tip 保持锁定。

## 单变量结论

四组都复用 exact resolution-192 fluid data，固定 `mesh_particle_radius=9.0`、`mesh_concave_lower=0.4`、`mesh_smoothen_pos/neg=1/1`，只修改 `mesh_concave_upper`：

| upper concavity | source volume error | temporal drift | outside cup + 1 voxel | max components | 结论 |
|---:|---:|---:|---:|---:|---|
| 3.50 | 4.40% | 1.55% | 7.68% | 3 | 体积通过、containment 失败 |
| 2.75 | 6.24% | 1.61% | 5.88% | 3 | 两项失败 |
| 2.00 | 12.40% | 2.42% | 1.72% | 10 | 体积、containment、碎裂失败 |
| 1.25 | 49.60% | 6.23% | 0.96% | 39 | 仅 containment 通过，体积、漂移、碎裂失败 |

降低 upper concavity 确实单调减少 measured outside fraction，证明默认重建器的 concave fill 参与了边界扩张；但改善以剧烈丢失净体积、更多组件和最终 temporal drift 失败为代价。没有任何 cell 同时通过冻结的五项门槛。

默认 3.50 control 完全复现 attempt-30 的 radius-9.0 指标：source error `0.04402087`、drift `0.0154918`、outside `0.07675232`。因此差异可归因于本轮唯一变量，而不是 cache 或测量漂移。

## Pipeline 与资源

- 4 次 Blender start；
- 4 次 fluid mesh bake；
- **0 次 fluid data bake**；
- 0 次 render、network call 或 engine remote write；
- 四组 process wall time 约 82.64、82.62、83.11、84.71 秒；
- work root 约 136.8 MB；
- retained data 与 retained attempt manifest 保持 exact。

## 停止与下一诊断

按预注册规则，停止继续调整 `mesh_particle_radius`、concavity 或 smoothing。现有 component bounds 给出一个更具体的底层线索：

- frame 4–7 出现一个固定 `+0.0000047004 m³`、100% outside 的小正体积组件，world Z 范围约 `0.0312..0.0531 m`，低于杯内底面加一体素边界；
- 同期主正体积外壳的最低 world Z 约 `0.05704..0.05714 m`，仅略低于当前 bottom limit；其 outside fraction 从约 2.35% 增至 9.81%。

下一步不再调表面，而是在 fresh copied result 上做零 bake、零 save 的逐轴 containment 诊断：分别统计 radial、below-floor、above-rim 以及交集，并把每个 outside 顶点绑定到 signed component。只有该诊断能区分“底层粒子穿过杯底”“重建壳层轻微进入杯底”和“containment reference 与真实杯形不一致”。
