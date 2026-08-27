# B52-D10 · Blender multipart temporal adapter holdout 无效结果

日期：2026-08-27

## 正式判定

`BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED`

Base failure：`SCENE_STRUCTURE`。冻结 analyzer 同时记录 `ANIMATION_STRUCTURE=false`。按预注册规则，D10 adapter 不得晋级为 production contract；本次正式 root 不得删除、覆盖或在修改 verifier 后重跑。

这是一项 verifier contract 的反例，不是 Blender pass payload 的反例。两个层面必须分开陈述：

- **正式事实**：34 个 attack 没有执行，因为 base contract 在 attack replay 之前失败；独立 audit 因此为 `FAIL`。
- **测量事实**：Vector、Depth、Object Index、multipart layout、adapter byte reconstruction、两次 source repeat 与两次 adapter repeat 的全部 payload gates 都通过。
- **禁止推论**：不能因为 payload measurements 通过，就把正式 verdict 改写成 supported。

## 失败原因

冻结 analyzer 用 JSON double literal 直接与 Blender RNA 返回值做 Python 逐值相等比较。Blender 将多项 RNA 浮点属性存为 float32，source report 忠实记录了读回值。因此语义相同的指定值在序列化后并不具有相同的 JSON 数字文本或 Python float 数值。

首个 source cell 的代表性差异：

| 字段 | spec/analyzer 期望 | Blender RNA 读回 |
|---|---:|---:|
| camera.orthoScale | 17.3 | 17.299999237060547 |
| BFS_MOVER.location.x | -0.7 | -0.699999988079071 |
| BFS_MOVER.location.y | 0.3 | 0.30000001192092896 |
| BFS_NEAR.scale.x | 0.8 | 0.800000011920929 |
| BFS_TOP_MARKER.scale.y | 1.1 | 1.100000023841858 |
| BFS_BOTTOM_MARKER.location.x | -2.4 | -2.4000000953674316 |

同一 float32 表示差异也进入 mover 的 Action keyframe values，导致 `ANIMATION_STRUCTURE=false`。scene name、frame、object roster、types、pass indices、action layer/strip/channel-bag/data-path/axis/frame/interpolation 均未观察到结构性偏离。

因此可证伪定位是：**D10 的 exact structural serialization oracle 没有把 Blender RNA 的 float32 storage semantics 纳入规范。** 这是事前契约设计错误，不能用事后 tolerance 修复同一次 holdout。

## 仍然成立的正式测量

一次且仅一次正式矩阵创建：12 个独立 Blender 5.2 Cycles CPU source processes、6 个独立 adapter processes、1 个 analyzer process，共 19 个唯一 child PID、12 次 ray render、0 个 source `.blend`、0 个 external asset。

- object motion：XY endpoint p99/max `7.62939453125e-6 px`；ZW `8.529922399520072e-6 px`；nearest wrong median `4.47213595499958 px`；
- camera motion：最坏 endpoint max `3.0517578125e-5 px`，p99 `1.52587890625e-5 px`；nearest wrong median `8.06225774829855 px`；
- static：XY/ZW max `3.0517578125e-5 px`，p99 `1.52587890625e-5 px`，在预注册非零容差内；
- Depth：60/60 owner-frame-repeat rows 通过，最大误差为 0；
- Object Index probes：60/60 精确；raster orientation 通过；
- source decoded repeat：12/12 pass comparisons exact；
- canonical adapter repeat：3/3 fixtures 的 7 arrays exact；
- independent adapter replay：6/6 cells、42/42 arrays exact；
- diagnostics：12/12 PNG 与 sidecar 完整且可重开。

这些数据支持一个后续假设：真实 Blender 5.2 pass 很可能满足 `Vector.XY = previous_screen-current_screen`、`Vector.ZW = current_screen-next_screen`，且 D9.1 adapter motion 很可能是 `(-X,-Y)`。由于 D10 正式 verdict 失败，这只能作为 D10.1 的设计证据，不能作为 production promotion。

## 身份与独立审计

- spec SHA-256：`147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566`
- preflight SHA-256：`853ad3b15e4952749897f5bbd0a892828c5e7531a2ef4150bed78acf6d7ce484`
- receipt SHA-256：`c7a3f3162e6d10a2d6bdfe445262106f95c20a3e716ecaf05fe194579240a066`
- result SHA-256：`0d28fb0d520a9f1ca493e952d492642698c72591e9d328dba7a71498dc3be8a1`
- audit file SHA-256：`c47a74042e27716ab1fbac9f78aaf53f12fb631038f79d683710de7d1162ad5e`
- audit self-hash：`5ff8f88542f37f4bad4e2b9bf6bc2cf76aa02b8ffbfdfc3ef7e2e963c3a12e9d`

Audit 正确报告 `FAIL`：parents、frozen tools、receipt/result self-hash、operation boundary、12/12 source artifacts、6/6 adapter replay 与 12/12 diagnostics 均通过；attack replay 为 0/34，因此不能给出 PASS。

## 后续边界：D10.1

D10.1 必须是新的预注册实验，而不是 D10 rerun：

1. 在任何 D10.1 tool 或 formal output 前冻结 float32 canonicalization 规则；对于声明为 Blender RNA float 的字段，oracle 必须先执行 IEEE-754 binary32 round-trip，再做 exact structure comparison。
2. integer、enum、name、roster、topology 与 operation count 继续 exact，不允许用全局 epsilon 掩盖结构错误。
3. 使用新的 resolution、ortho scale、owner IDs、geometry、object/camera trajectories 与正式 output root；D10 EXR 不得充当新 holdout 输入。
4. 保留 D10 的 Vector、static、Depth、ownership、repeat、adapter、diagnostic、process 与 attack thresholds，不因这次失败降低 payload gate。
5. 增加 canonicalization sensitivity attacks：跳过 float32 round-trip、错误地量化 integer/name，以及对已 canonical 值作一 ULP 篡改都必须被拒绝。

D10.1 全部通过前，Blender production passes 仍不得接入 D9.1 production chain。
