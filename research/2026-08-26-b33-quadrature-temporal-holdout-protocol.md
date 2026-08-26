# B33 formal protocol · Q8 consecutive-frame temporal-proxy holdout

日期：2026-08-26（America/New_York）

状态：`PREREGISTERED_BEFORE_FORMAL_TOOLING_OR_OUTPUTS`

## 正式问题

在与派生区间完全不相交的八个连续 frame 上，固定 Q8 是否仍能在 scene-linear temporal-error delta 上接近 NATURAL32，并保持对 Q4 的显著优势？

机器可读合约为 `specs/quadrature-temporal-holdout-spec.v0.1.json`，冻结 SHA-256 为 `79fe033683352c4b8295d47bfca112ace7c7a9440ffdaa992933999fb8468ddf`。任何正式 renderer、analyzer、runner 或正式 EXR 都必须在本协议提交之后出现。

## 新样本与净执行

- 正式 frame：`74–81`；派生 frame `121–128` 全部排除。
- NATURAL32 A/B、REFERENCE1024 A/B、Q4 四点 A/B、Q8 八点 A/B。
- 每个 cell-replicate 启动一个 fresh Blender PID，在同一进程内按升序渲染八帧。
- 合计 28 个唯一 PID、224 次 render、224 个新 EXR。
- B33 derivation EXR 不得进入正式分析；正式 work/evidence 必须从空目录开始。

## 冻结指标

保持派生定义：`E_m,t = I_m,t - R_t`，`D_m,t = E_m,t - E_m,t-1`。每个 transition 分别在 global、相邻空间边缘 exact-top-k 并集、参考运动 exact-top-k 三个域上计算。top-k 始终以 magnitude 降序，再以 C row-major flattened pixel index 升序打破并列。

## 从派生值到正式门槛

派生 Q8/NATURAL 最大值为 global `0.83436`、edge `0.94248`、motion `0.98847`。正式 every-transition ceilings 冻结为：

- global `≤ 1.00`；
- spatialEdgeUnion `≤ 1.10`；
- referenceMotionTopK `≤ 1.10`。

派生 Q8/Q4 全域最大值 `0.58030`，最大域均值 `0.57036`。正式门冻结为：

- 每个 transition、每个域 `≤ 0.75`；
- 每个域的七-transition mean `≤ 0.65`。

这些是先于正式输出的 round ceilings，分别保留约 11–29% 的乘性余量。Q4 的派生时间误差明显高于 NATURAL，因此不人为给 Q4 设置 near-natural 通过门；Q4 在正式实验中保留为可重复的成本曲线中间点。

## 其余正式门

- REFERENCE1024 temporal reliability ratio 每 transition、每域 `≤ 0.05`；
- Q4/Q8 composite A/B 每帧 float exact；
- Q4/Q8 temporal delta A/B 每 transition、每域 float exact；
- 所有 ratio denominator finite 且大于零；
- 身份、进程、文件、哈希、绑定与负向攻击全部通过。

全部通过才得到 `Q8_TEMPORAL_PROXY_HOLDOUT_SUPPORT`。否则按冻结 precedence 保留 component failure；任何身份或设计错误优先为 `IDENTITY_OR_DESIGN_INVALID`。

## 非声明

通过也不能声称人眼不可见闪烁、运动电影感、motion-blur 正确、编码交付稳定或人类偏好。REFERENCE1024 是 proxy，motion blur 关闭，场景/机器/后端覆盖有限。独立人类盲评仍是另一条尚未完成的证据链。

## Freeze statement

本提交时，正式 B33 renderer、analyzer、runner 与 `experiments/quadrature-temporal-holdout-v0-1/` 输出均不存在。
