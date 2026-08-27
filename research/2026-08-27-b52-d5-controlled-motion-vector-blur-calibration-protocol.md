# B52-D5 · 受控运动 Vector Blur 任务校准协议

日期：2026-08-27

## 研究问题

D4 的 36 个 Blender 进程全部成功，但两个保留场景的 baseline Vector Blur 都没有一个像素越过 `1/65536` task-effect 门。候选输出相同因此没有判别力。D5 不再问 adaptive Vector 是否安全，而先问更前置的问题：能否用两个确定性的运动 fixture 和一个静态 negative control，把 Blender 5.2 Vector Blur 校准为敏感、shutter 剂量有序且跨净进程可复现的任务 oracle？

## 预注册之前的探索证据

探索 fixture 使用正交相机、分层平面、线性移动体和静态遮挡体。两次失败均保留：

1. Blender 5.2 拒绝 `BLENDER_EEVEE_NEXT`，本机 enum 为 `BLENDER_EEVEE`；
2. Blender 5.2 layered Action 不再暴露 `Action.fcurves`，准确路径是 `Action.layers[].strips[].channelbags[].fcurves[]`。

随后 EEVEE 与 Cycles CPU probe 都产生强响应。Cycles 的 Vector 最大幅值为 51.200012 px；shutter 0.25/0.5/1.0 的 RGB 最大变化为 0.872852/0.985832/1.039586，RMSE 为 0.042492/0.060361/0.086440。它们只用于决定正式问题，不进入正式结果。

## 三个 fixture

所有 fixture 都从 factory state 生成，不打开 `.blend` 或外部资产。共同使用 512×288、正交相机、蓝色背景、红色前景平面、黑色静态遮挡平面和一盏 Area light。

- `OBJECT_OCCLUSION_X`：前景平面在 frame 0/1/2 的 x 为 −1/0/+1，跨越静态遮挡体；
- `CAMERA_PAN_X`：相机在 frame 0/1/2 的 x 为 −0.5/0/+0.5，分层几何保持静止；
- `STATIC_CONTROL`：相机和所有几何都没有 keyframe。

每个 fixture 用两个全新 Blender 进程在 frame 1 渲染 Cycles CPU multipart EXR。固定 16 samples、seed 20260827、adaptive/denoise/motion blur/persistent data 全关、四线程。八个 decoded part 必须在两重复之间逐位完全一致。

## 真实 compositor 矩阵

每个 source repeat 分别进入四个全新 Blender 进程，shutter 为 0/0.25/0.5/1.0，共 24 个 compositor 进程。节点只允许 Image、Vector Blur 和 Group Output；输入固定为该 source 的 Combined、Vector 与 Depth。Vector Blur Samples=32，CPU compositor、固定四线程，输出 RGBA32 ZIP EXR。

总计 30 个 Blender 进程、30 次 render call，其中 6 次为 Cycles source render、24 次只执行 compositor。所有 PID 必须唯一；12 个 fixture × shutter 两重复输出必须 decoded exact。

## 冻结任务门

两个 moving fixture 都必须满足：

- Vector maximum 在 8–128 px，p99 ≥8 px，超过 1 px 的像素至少 2,000；
- shutter 0 输出相对 Combined 的 RGB maximum ≤`1/65536`，且越门像素为零；
- shutter 0.5 的 RGB maximum ≥0.05、p99 ≥0.005、RMSE ≥0.005，超过 `1/4096` 的像素至少 1,000；
- shutter 0.25→0.5→1.0 的 RGB maximum、p99、RMSE 都严格上升，且 shutter 1 / 0.25 的 RMSE 比至少 1.5。

静态 control 必须满足 Vector maximum ≤`1/1024`、p99 ≤`1/65536`，所有 shutter 的 RGB maximum ≤`1/65536` 且越门像素为零。

这些门在正式 CAMERA_PAN 与 STATIC 输出出现前冻结。失败不允许修改门或删除 fixture。

## 诊断与审计

每个 fixture 固定输出 Combined、Vector magnitude、shutter 0.5 RGB maximum absolute error 三张 PNG，共九张。Vector 使用 `[0,64]`，blur error 使用 `[0,1]` 的固定 `(t,t²,0)` RGB8 映射；每张图都有 canonical sidecar 和 decoded reopen 检查。

20 个攻击覆盖 parent/runtime identity、fixture/Action 结构、source/compositor process 与 output roster、两层 repeat exactness、moving sensitivity、shutter-zero、dose、static control、diagnostic、operation boundary 和 self-hash。独立 analyzer replay 与 audit 是结论的一部分。

## 判定与非主张

只有全部门通过，结论才是 `CONTROLLED_VECTOR_BLUR_TASK_CALIBRATION_SUPPORTED`，并只允许下一步冻结一个 fresh controlled-motion adaptive Vector holdout。任何失败都给出 `CONTROLLED_VECTOR_BLUR_TASK_CALIBRATION_INVALID`，随后停止用 Blender Vector Blur 作为本分支 oracle，改测 deterministic warp 或独立 optical-flow task。

D5 不评价 adaptive profile，不是 production shot、电影感、视觉质量、遮挡正确性或人类偏好证据；不能修改 D2、D3 或 D4 的既有结论。
