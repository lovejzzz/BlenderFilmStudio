# B52-D12.8 · 真实刚性运动 / 反遮挡 adaptive risk fresh holdout 协议

日期：2026-08-27
状态：`PREREGISTERED_BEFORE_FORMAL_TOOL_OR_OUTPUT`

机器可读规范：`specs/blender-projective-motion-disocclusion-adaptive-risk-holdout.v0.1.json`
Spec SHA-256：`67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4`

## 结论边界先冻结

D12.7 已经表明，冻结的局部风险门在三组新静态 Blender 几何上满足候选自身的误差、风险保守性、压力与覆盖门；但预注册 analyzer 把 radius-3 参照的 production check 也并入了总 conjunction，因此总体只能保留为 bounded。D12.8 不改写这个历史结果。

本实验在看到任何新 render 前明确规定：radius 3 只是 paired diagnostic。它的误差、覆盖率与压力测量全部报告，但不能让 adaptive candidate 通过、bounded 或失败。候选结论只由其自身的身份、运动投影、遮挡拒绝、误差、风险、覆盖率、压力与静态 control 决定。

这不是降低候选标准。候选继续使用 D12.7 的原公式与 inclusive `1/1048576` 风险阈值，并继承 98% 总 retention、95% per-owner retention 与零 risk-underbound 要求。改变的只有 comparator 的裁判身份，而且已经在新证据出现前冻结。

## 两道依次执行的门

真实运动不能只看颜色误差。D12.8 把历史复用拆成两个不可交换的阶段：

1. **物理有效性门**：用当前像素的解析可见面、刚体局部点、前一帧物体 / 相机 transform、Object Index、alpha 与 previous Depth，判定历史是否属于同一表面点；
2. **数值风险门**：只对物理有效且通过当前 radius-2 owner erosion 的像素，计算 D12.7 冻结的四 tap contrast bound，并以 `risk <= 1/1048576` 决定是否使用 bilinear history。

任何结构无效像素与任何 risk-rejected 像素都必须逐 float32 复制 current RGBA。颜色目标不得参与结构有效性判定。

## Fresh fixtures

四组场景都从 Blender factory state 生成，使用新的 raster、ID、pass index、轨迹、材质系数与输出路径：

- `RIGID_OBJECT_SWEEP_DISOCCLUSION_149X97`：前景矩形刚体横向扫过背景，制造真实 occlusion / disocclusion；不同 Object Index 应触发 `INVALID_OWNER`；
- `CAMERA_DOLLY_YAW_PARALLAX_BOUNDS_163X101`：两层静态平面配合真实 camera dolly + yaw，制造视差与出界历史；
- `SAME_INDEX_DEPTH_REVEAL_173X107`：前景与背景故意共用 Object Index，owner-only 规则必须错误接收至少 24 个 primary 像素，而 transform-predicted previous depth 必须把它们拒绝为 `INVALID_DEPTH`；
- `MULTI_OWNER_STATIC_CONTROL_127X83`：两层静态 control，保留 Blender 已知的非零 Vector floor，不再使用已被 D12 反例否定的“静态误差必须绝对为零”。

每个 fixture 有两个 clean repeats；每个 repeat 只渲染 previous frame 0 与 current frame 1，动画仍冻结 frame 0–2 以生成并校验 Vector.XY/ZW。

## 独立投影、可见性与深度 oracle

对 top-left raster 的 pixel center，独立 analyzer 以 Blender camera local `-Z`、XYZ Euler、horizontal sensor fit 实现 pinhole projection。它把 current ray 与所有有界局部 `z=0` 平面相交，选择最近正深度命中，并得到不依赖 Object Index 的 `analyticOwnerId`。

随后把 current 命中点逆变换回该 owner 的 local space，再应用 previous object transform 并投影进 previous camera：

```text
expected Vector.X = previousX - currentX
expected Vector.Y = currentY_top - previousY_top

q_x = currentX + Blender Vector.X
q_y = currentY_top - Blender Vector.Y
```

previous Depth 比较的目标不是 current Depth，而是同一个 local surface point 在 previous camera 中的预测深度。analyzer 禁止导入 `bpy`、`bpy_extras`、`mathutils` 或 tested consumers。

## 冻结判定

### 必须通过的安全门

- Vector endpoint absolute maximum ≤ `1/1024 px`，p99 ≤ `1/4096 px`；
- previous-depth relative error ≤ `1/1024`；
- 结构无效历史 false acceptance 为 0；
- 所有结构无效与 adaptive-rejected 像素逐 float32 等于 current；
- adaptive RGB maximum 与 RMSE 都 ≤ `1/1048576`；
- local risk underbound RGB sample 数为 0；
- Python / Node payload、独立 replay、repeat、parent、runtime、process 与 typed-envelope identity 全部通过；
- static control Vector component maximum ≤ `1/4096 px`，adaptive RGB maximum ≤ `1/1048576`。

### 必须通过的效用与压力门

- 每 cell radius-2 与 adaptive 都至少 256 pixels；
- 每个 analytic owner 至少 64 adaptive pixels；
- adaptive / radius-2 total retention ≥ 98%；
- 对至少 100 个 radius-2 pixels 的 owner，per-owner retention ≥ 95%；
- 每个 moving primary fixture 至少有 1 个 adaptive risk rejection；
- 每个指定 fixture 达到其冻结的 `INVALID_OWNER`、`INVALID_BOUNDS` 或 `INVALID_DEPTH` stress 数量；同 pass-index fixture 的 owner-only counterfactual 至少错误接收 24 pixels。

### 三分支 verdict

- 全部门通过：`PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_SUPPORTED`；
- 安全、身份、物理拒绝与误差门通过，但 coverage 或 risk-stress 不足：`PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_SAFE_BUT_COVERAGE_NOT_SUPPORTED`；
- 任一身份、投影、遮挡拒绝、invalid fallback、risk conservatism、adaptive quality、static control、process 或 audit 门失败：`PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_NOT_SUPPORTED`。

radius-3 的任何测量都不得进入以上三条分支。

## 正式矩阵与磁盘准入

正式矩阵冻结为 74 个含 audit 的 unique child processes：16 个 Blender Cycles CPU source、8 个 adapter、16 个双语言 consumer、32 个双语言 typed-envelope encoder、1 个 analyzer 与 1 个 audit。模型调用和网络调用必须为 0。

Projected write 为 64 MiB，formal root 创建前可用磁盘必须在扣除该预算后仍不少于 100 GiB。当前 formal root、preflight root 与八个新 formal tool paths 均不存在；当前正式 render 和 measurement 数都是 0。

工具完成后必须先冻结 Git identity，再运行不写 formal root 的 preflight。预检只有在 parent/runtime/tool hash、Blender API/graph probe、contract tests、路径 freshness 与磁盘准入全部通过时，才允许 formal runner 一次性创建正式根目录。

## 非主张

D12.8 只覆盖 compiler 已知 transform 的不透明、刚性、有界平面 owner。它不覆盖曲面、骨骼角色、形变、透明、Cryptomatte fractional coverage、毛发、粒子、体积、motion blur、DOF 或 noisy lighting，也不证明 temporal denoising、主观稳定性、电影感、角色一致性、生产渲染或跨平台等价。

即使 supported，也只允许下一项 curved / deforming owner preregistration；不能直接升级为生产策略。
