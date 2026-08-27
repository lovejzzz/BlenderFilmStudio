# B52-D4 · Blender 5.2 Vector Blur 任务语义派生结果

日期：2026-08-27
结论：`ADAPTIVE_VECTOR_BLUR_SEMANTICS_DERIVATION_INVALID`
主失败：`BASELINE_EFFECT`

## 一句话结论

D4 没有证明候选 Vector pass 安全，也没有证明它不安全。它证明了更前置的问题：在这两份保留场景上，冻结的 Blender 5.2 Vector Blur 任务几乎没有产生可测的基准运动模糊，因此不是一个有信息量的下游判别器。

## 正式执行

- 36/36 个全新 Blender 5.2.0 LTS 进程成功退出，PID 全部唯一，超时为零；
- 36 次 `bpy.ops.render.render` 只用于执行 compositor，Cycles 光线追踪渲染为零；
- 36 个 RGBA32 ZIP EXR 全部存在且有限，总计 51,596,604 bytes；
- 18/18 个 profile × variant 两重复组的解码浮点像素逐位完全一致；
- 54/54 个父 EXR、18 个实际 compositor source 与五个父文件在运行前后保持 identity；
- 12 张固定映射 PNG 与 12 个 sidecar 均生成并在审计重放中匹配。

36 个进程累计墙钟时间 72.760555 秒，单进程 1.997734–2.042612 秒。这是本机 Apple M4 Max、CPU compositor、固定四线程的实测，不是跨机器性能结论。

## 为什么实验无效

预注册要求：基准 Vector Blur 输出相对同一份基准 Combined 输入，两个场景都至少有一个 RGB 像素的绝对变化大于 `1/65536`。这是 task-validity gate；若它失败，后续“候选输出看起来相同”不能解释成候选安全。

实测：

| 场景 | baseline motion magnitude max | blur 相对 Combined 的 RGB 最大误差 | 超过 `1/65536` 的像素 | 结果 |
|---|---:|---:|---:|---|
| TABLETOP_WIDE | 0.90632667 | 0.0000038147 | 0 | FAIL |
| INTERIOR_CHAIR | 0.00005840 | 0.0000001192 | 0 | FAIL |

TABLETOP 的最大 motion 仍不足一个像素；在 `Shutter=0.5` 下，冻结任务的有效位移更小。INTERIOR 基本是静态向量场。两者都没有越过冻结的最小 task-effect 门。

16 个 candidate–baseline 输出对的 RGB 最大差全部为零。TABLETOP 的八个候选在局部分类器上形式通过，INTERIOR 八个全部失败；但由于基准任务本身无效，这些行只能作为描述性观察，不能生成任何 `vectorTaskTolerableProfiles`。最终候选列表为空。

## 保留的失败与分析修订

正式 compositor 运行成功后，第一版冻结分析器在严格 JSON 序列化时失败：`numpy.bool_` 不是 Python JSON encoder 接受的内建 `bool`。原始 receipt、failure JSON 与 traceback 均被保留。

后输出修订提交 `6d64a5ca2f2b4a83bc9f51fa2054133639c3e762` 只做三件事：把两个测量布尔量显式转换为内建 `bool`、增加严格 JSON 回归测试、让审计验证修订边界。它没有改变 spec、阈值、图、EXR 或任何 compositor 输出；36 个正式 EXR 全部复用，重渲染为零。

修订后的分析可字节级重放，但 19 个攻击中仅 12 个到达预期 failure route；其余后置攻击被更早的真实 `BASELINE_EFFECT` 主失败遮蔽。独立审计因此诚实返回 `FAIL`，同时报告：54/54 父工件、36/36 输出、24/24 diagnostic 文件、全部修订约束与结果字节重放均匹配。这里的 `FAIL` 表示实验没有建立可用推断，不表示证据丢失。

## 不能声称什么

- 不能声称 adaptive Vector pass 已经安全；
- 不能把输出相同解释成视觉无差异，因为指定任务没有先证明自己敏感；
- 不能修改 `1/65536` 门来挽救结果；
- 不能把 TABLETOP 的局部通过推广到 INTERIOR 或任何新场景；
- 不能修改 D2 的 production negative、D3 的 Normal/Crypto 失败或 INTERIOR beauty blocker。

## 下一步：先造一个会动的验证场景

D5 不应继续在同一静态任务上调阈值。更有证据支持的下一步是预注册一个 task-validity calibration：在新的、受控的 Blender 动画场景中制造已知像素位移、遮挡与出画/入画边界，先证明 Vector Blur 对 baseline motion 有稳定、非平凡且可重复的响应，再盲测 adaptive Vector 差异。

建议把 D5 分成两层：

1. baseline-only calibration：只用基准 profile，在不读取候选输出的情况下冻结运动幅度、shutter、样本数和非平凡 effect 区间；
2. fresh holdout：换随机种子或镜头，把冻结任务应用到 baseline 与候选，要求任务敏感性、decoded repeat exactness、遮挡边界和输出误差同时过门。

如果 calibration 仍无法让 Blender 5.2 Vector Blur 对已知运动产生稳定响应，就应停止把该节点当作 Vector pass 的验证 oracle，改用几何可解释的 deterministic warp 与独立光流任务。

## 身份

- preregistration spec SHA-256: `e8635a1507eb5a5e8bfd950dc02fc4630a7202fd9af14b5510a991359f2e439f`
- original tool freeze: `842af415f7a29393a81ac94b24744f05d440baa5`
- serialization amendment freeze: `6d64a5ca2f2b4a83bc9f51fa2054133639c3e762`
- original receipt SHA-256: `bb3233c04242bf1179c935cc2fb7efc2812cb7d0aaf6e7793a3e75ad0c1f1b90`
- amended receipt SHA-256: `bb45fe5a3e38e032c66054268170bf92d8a173db968ddb1a18420868338895e4`
- result SHA-256: `6c55a5b93a95eb6f6070c29c8cfc10ba746121fb5ec9b04de062ae2407ca12d9`
- audit SHA-256: `c019a3272287f2b6c49060eae1fa8e8723cdada7a0d7c4032d22cef1918c0933`
- retained analysis failure SHA-256: `897a93fc62c8164f7b203a4ba079015dbe73c0581c919a2d52ad252756bba4ec`
