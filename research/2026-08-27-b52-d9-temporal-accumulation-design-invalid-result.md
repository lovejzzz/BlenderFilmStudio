# B52-D9 · Temporal accumulation design-invalid 结果

日期：2026-08-27

## 判定

`B52_D9_DESIGN_INVALID_BEFORE_FORMAL_OUTPUT`

D9 没有进入正式矩阵。两个 development-only producer 在全部四个 fixture 上生成了完全相同的十组 input/ground-truth/output arrays；正确 validity mask 与 resolved RGBA 都逐位命中 analytic ground truth。但冻结的 wrong-sign sensitivity control 在两组运动 fixture 上不够敏感，因此 designated task 不能成为 motion-direction oracle。

## 保留的反例

冻结门要求 wrong-sign motion 同时达到：

- wrong pixels ≥32；
- maximum absolute error ≥0.25。

实测：

- FOREGROUND_CROSSING：496 wrong pixels，但 maximum=0.0625，FAIL；
- CAMERA_PAN：2,026 wrong pixels，但 maximum=0.0625，FAIL；
- DEPTH_SWAP_SAME_ID：184 wrong pixels，maximum=0.640625，PASS。

Naive-history control 在两个 applicable fixture 均通过：FOREGROUND 248 pixels / 0.71875，DEPTH_SWAP 552 pixels / 1.015625。STATIC_CONTROL 2,993/2,993 history valid，resolved exact。

## 原因定位

FOREGROUND 与 CAMERA 的同一 layer 内使用 constant color。wrong-sign lookup 大多仍落在相同 ownership 与 depth，因此 history validation 合理地接受它；错误只来自 development fixture 的 ±1/16 complementary noise，maximum 自然被限制在 0.0625。错误方向确实改变了大量像素，却达不到已冻结的 material-error magnitude。

这不是调低 0.25 门槛的理由。它说明 D9 的指定任务缺少 spatially varying same-surface signal，不能区分“方向错误但仍在同一层”的重投影。

## 决策

不实现 encoder、Blender worker、formal runner 或 audit，不创建正式输出根目录。两个 development producer 与 observation 被保留。

下一步 D9.1 必须在任何工具前完整冻结 surface-local checker/stripe texture、box coordinates、motion 与 expected control minima，并使用从未执行过的新 resolution/trajectory。D9.1 仍保留 0.25 maximum gate，不复用 D9 的四个 arrays。

D9 invalid 不否证 layer/depth validity 算法；它只否证当前 designated task 足以验证 motion direction。
