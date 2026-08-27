# B52-D9.1 · Textured layer/depth temporal accumulation fresh holdout 协议

日期：2026-08-27

## 研究问题

D9 development smoke 没有否证正确 accumulator：Python/Node、validity 与 clean target 全部 exact。它否证的是 designated wrong-sign task。constant-color same-surface region 即使取错位置，ownership/depth 仍可能合法，差异只有 ±1/16 noise，无法越过冻结的 0.25 magnitude gate。

D9.1 不降低阈值。它在任何新工具前冻结全新的 resolution、box、motion 与 surface-local texture，问错误 motion direction 是否会在相同 layer/depth 内选错空间结构，同时正确 direction 仍逐位恢复 analytic target。

## Freshness 与纹理

D9.1 不复用 D9 的四个 resolution、box、motion、array 或 constant-color surface。四个新 raster 是 103×63、107×61、89×49 与 71×43；运动分别为 9 px foreground crossing、(7,−4) camera pan、−5 px same-ID depth swap 与 static zero。

BACKGROUND_CHECKER、FOREGROUND_STRIPE、OLD_PATCH 与 NEW_PATCH 的 selector 和两组 RGBA 值都写入 spec。所有值是 binary-exact float32，包含 negative 与 HDR。移动表面的 current local coordinate 显式减去 frame offset，使正确 `q=(x−dx,y+dy)` 取回同一个 surface-local texel；wrong sign 会在 ownership/depth 仍相同时取到不同 checker/stripe phase。

## Ground truth 与 exact accumulation

输入包括 previous/current RGBA、positive depth、float32 integer layer ID 与 integer motion。analytic validity 直接由已冻结 trajectory 生成，并独立满足 bounds、layer ID、depth `max(1,z)/1024` 和 alpha 条件。

valid pixel 的 previous/current texel 加入等量反向 binary-exact noise，0.5 average 必须等于 clean target；invalid current 直接等于 clean target。Python scalar 与 Node JavaScript 必须对全部十组 arrays byte exact，且 validity 与 resolved output 分别 exact 命中 analytic ground truth。

Naive history 在 foreground crossing 与 depth swap 上各需 ≥32 wrong pixels、maximum ≥0.25。Wrong-sign motion 在三组 moving fixture 上各需满足同一门。Static control 必须全部 history valid 且 resolved exact。

## D8 bridge 与正式矩阵

每份 producer resolved RGBA 由独立 OpenImageIO process 写为 RGBA/FLOAT/ZIP/Raw EXR，再进入两个 fresh Blender 5.2 CPU compositor process。graph 仍只有 `Image → Group Output`，输出 RGBA32 ZIP EXR。

正式矩阵：4 Python + 4 Node + 8 encoder + 16 Blender = 32 个唯一 PID；16 次 compositor render，0 Cycles ray render，0 source `.blend`。encoder decode、16 份 Blender decode、repeat 与 producer convergence 都是 exact-only。

## 判定与下一边界

30 个 attacks 覆盖 D8、D9-invalid、freshness、runtime、全部 arrays/ground truth、两个 sensitivity control、encoder、Blender graph/output、diagnostics 与 self-hash。全部通过才可写 `LAYER_DEPTH_TEMPORAL_ACCUMULATION_HOLDOUT_SUPPORTED`。

通过只允许下一步预注册真实 Blender multipart adapter holdout：校准 Vector 四分量的 previous/current pair 与方向，把 Depth/ownership 转成 D9.1 canonical input。D9.1 不证明 Blender Vector、subpixel filter、半透明、motion blur、DOF、temporal denoising、电影感或人类偏好。
