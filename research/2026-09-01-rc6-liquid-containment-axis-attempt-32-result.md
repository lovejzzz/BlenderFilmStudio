# RC6 液体 containment 逐轴诊断 attempt-32

`RC6-2026-09-01-containment-axis-attempt-32` 以一次 Blender start、零 bake、零 save、零 render 在完整 fresh candidate copy 上完成七帧逐轴诊断。execution receipt 为 `PASS_EXECUTION`。

首版独立审计保留为 `FAIL 23/24`：唯一失败项 `configurationExact` 把杯外圆 float32 顶点错误假设为同一个十进制 `0.15`，并把 F6 已冻结在 blend 中的 cup effector `surface_distance=1.5` 错写成 `0.0015`。C1 只修正这两个 expected configuration 字段，不启动 Blender、不改 result/receipt/阈值；独立审计通过 `26/26`。

## 峰值原因

峰值发生在 frame 7：

- outside-union：7,814 / 101,808 = `7.675232%`；
- radial：`0`；
- above-rim：`0`；
- below-floor：`7,814`；
- dominant axis：`belowFloor`；
- dominant share of outside union：`100%`。

按 signed component：

- 主正体积外壳：6,584 / 67,112 顶点 below-floor，最低 cup-local Z `-0.16292512 m`，比 `bottomLimit=-0.1626041667 m` 深约 `0.321 mm`；
- 嵌套负体积内壳：0 outside；
- 固定小正体积组件：1,230 / 1,230 顶点 below-floor，cup-local Z 范围约 `-0.18877657..-0.16692001 m`，signed volume `+0.0000047004 m³`。

frame 1–3 的三个 axis count 均为零；frame 4 起只出现 below-floor，并逐帧增加。由此排除杯壁半径与杯口高度是当前 containment failure 的原因。

## 几何与权限

raw cup mesh 复核出 inner rings 为 radius `0.09 m`、bottom `-0.16 m`、top `0.22 m`。outer radius 的 64 个 float32 顶点按十进制测量分成 `0.14999999 / 0.15000000 / 0.15000001`，这是表示差异，不是杯形变化。

正式计数：1 Blender start、0 fluid data bake、0 fluid mesh bake、0 blend save、0 render、0 network、0 engine remote write。source work、source candidate 与 copied candidate manifests 均保持 exact。

## 下一步

本诊断证明的是“可见重建网格在杯底下”，还不能证明底层 FLIP 粒子本身已穿透。下一步应在另一个 fresh copy 中零 save 地显式暴露/read-only 读取 FLIP particle system，分别对粒子位置与可见 surface 做相同 cup-local axis classification：

- 若粒子也 below-floor，修正 effector/fraction/push-out 或低分辨率碰撞参数后重新求解；
- 若粒子全在杯内而仅 surface below-floor，问题属于 isosurface 厚度/measurement envelope，不能用碰撞参数解释；
- 不得在未区分两者前继续提高 mesh radius、调 smoothing 或进入 tip/impact。
