# B52-D12.14-P1：Position-pass Vector oracle 开发验证协议

Date: 2026-08-28

Status: `PREREGISTERED DEVELOPMENT PROBE`

Scientific verdict: none

## 为什么 H1 的下一步不是调阈值

H1 已作为冻结工具失败封闭，没有科学 verdict。事后只读取证显示，NEITHER 的 27,383 个 registered pixels 中有 16,819 个具备同 Material-owner 的 previous bilinear support，但直接对 previous Z 做双线性插值后有 16,541 个未通过 predicted-depth gate，只剩 278 个 structural-valid 与 270 个 radius-2 witnesses。

误差具有明确的投影结构：线性 Z 插值相对解析 previous depth 的中位绝对误差为 `0.3819589932`、最大为 `0.4652322060`；改为 `1 / bilinear(1 / Z)` 后，中位数降至 `2.7539772e-5`、最大值降至 `1.8841765e-4`，16,819/16,819 全部通过原 relative-depth gate，并恢复 16,065 个 radius-2 NEITHER witnesses，恰好等于 H1 预登记前 zero-render raster pilot 的 16,065。这个结果指出 projective plane 应在 inverse-depth 空间插值，但它是 postfailure observation，不是 fresh confirmation。

H1 还有一个独立的仪器缺口：三个 fixture 的 pixel-center Vector oracle 最大误差分别为 `2.08074396e-4`、`1.52587891e-4` 与 `5.77159103e-4` pixel，均高于冻结的 `1/16384`。改变容差不能回答 oracle 是否比较了同一个物理样本。

## Blender 5.2 精确源码给出的可证伪解释

本机 Blender build hash `fbe6228777e7` 对应官方源提交 `fbe6228777e7d9afefcd61a413844e790ae75db7`。该提交的 Cycles data-pass 路径把 Depth 写为 `camera_z_depth(sd->P)`、Position 写为 `sd->P`，并从同一 `ShaderData` 调用 motion-vector 计算；rigid motion 路径也从 `sd->P` 出发，经 previous object transform 与 current/previous raster projection 后求差。

由此得到一个待实测的推论：H1 的 integer pixel-center ray 与 Cycles 实际 first-hit sample 并非同一个 oracle 输入；Position pass 才能绑定 Vector 使用的真实 world-space hit。P1 将新增 Position pass，并比较：

```text
P_current = Position.xyz
P_local   = R_current^T · (P_current - T_current)
P_prev    = T_prev + R_prev · P_local
V_expect  = project_prev(P_prev) - project_current(P_current)
```

对 top-left arrays，Y 分量仍使用 `currentYTop - previousYTop`。

## 冻结开发矩阵

P1 复用 H1 的 `RIGID_NEITHER_FRESH_197X139` 几何、动画、camera、Material/Object tokens、Cycles CPU、sample 1 与 seed，仅把 view-layer 名称改为 `BFS_D1214P1_MASTER` 并新增 Position pass。它进行两次新的 factory-empty current-frame render；不得复制 H1 EXR。两次 decoded passes 必须 byte exact，EXR container bytes 可以不同，但 metadata 差异只能来自 `Date`、`RenderTime`、`Scene`。

Position-owner pixels 至少 20,000；Position 必须 finite 并匹配 Material/Object tokens；Position 推导的 current camera Z 必须在 `1/16384` 内匹配 Depth；Position-based Vector oracle 与 zero next-vector 的最大绝对误差也都必须不高于 `1/16384` pixel。任一 gate 不成立即保留 negative development result，不修改 P1 后重跑。

## 边界

P1 只决定 Position 能否成为 H2 的 control oracle。它不能修复 H1、不能产生 H1 verdict、不能把 inverse-depth posthoc replay 变成正式证据、不能授权编译器晋级。无论 P1 结果如何，这个 fixture 与输出都永久排除在 H2 formal measurement 之外；H2 必须使用新 experiment ID、fresh fixture、fresh passes 与预先提交的工具和判定合同。

机器可读协议：`specs/blender-material-owner-rigid-directional-position-oracle-development.v0.1.json`。
