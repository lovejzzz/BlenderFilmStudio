# B33 protocol · deterministic quadrature temporal-error derivation

日期：2026-08-26（America/New_York）  
状态：`PREREGISTERED_BEFORE_TOOLING_OR_OUTPUTS`

## 问题

B32 只说明四个离散 frame 上，Q4/Q8 可重复且形成了 scene-linear reference-proxy 成本—质量曲线。它没有测试连续播放时误差会不会随帧抖动。B33 的问题是：在八个全新连续 frame 上，NATURAL32、固定 Q4 与固定 Q8 相对 dual-REFERENCE1024 proxy 的误差，其相邻帧变化量分别有多大？

机器可读合约是 `specs/quadrature-temporal-derivation-spec.v0.1.json`，冻结 SHA-256 为 `5630ed7cc9a43f9f195292296923ff7864625bad6b0dbad4a7eb7b7eeb4ab594`。本轮只负责派生正式阈值，不产生 temporal quality confirmation。

## 先冻结、后出图

- 连续区间固定为 frame `121–128`；不使用任何 B31/B32 单帧质量 frame。
- 每个 cell-replicate 启动一个新的 Blender 进程，并在同一进程中按升序渲染八帧。
- NATURAL32 A/B、REFERENCE1024 A/B、Q4 四点 A/B、Q8 八点 A/B，共 28 个唯一 PID、224 次 Blender render。
- 从空的 B33 work/evidence 目录开始；旧 EXR 不得充当输入。
- 输出为 960×540、scene-linear、RGBA float32 ZIP EXR；分析只使用 RGB。

## 为什么不直接比较相邻画面

镜头和物体真的在运动，所以 `I_t - I_(t-1)` 大并不等于闪烁。先定义每种方法相对参考的误差：

`E_m,t = I_m,t - R_t`

再定义 temporal error delta：

`D_m,t = E_m,t - E_m,t-1`

它衡量候选方法相对参考的偏差是否在相邻帧改变。仍不能等同于“可见闪烁”，但比原始帧差更接近要检验的数值问题。

## 三个冻结的观察域

每个 transition 都报告 RMSE 与 maximum absolute error：

1. `global`：全画面；
2. `spatialEdgeUnion`：参考图两端各自按 gradient magnitude 精确取 top 25,920，取并集；
3. `referenceMotionTopK`：按参考相邻帧 RGB 变化幅度精确取 top 25,920。

所有 top-k 都按 magnitude 降序、C row-major flattened index 升序打破并列，避免 B32 v0.1 的 25,920→25,921 问题复发。

## 派生有效性门，而非质量门

只有以下条件全过，数据才允许用来冻结另一个全新区间的正式阈值：

- REFERENCE1024 A/B temporal residual 相对 NATURAL32 的 ratio，在每个 transition、每个域都 `≤ 0.10`；
- Q4/Q8 composite A/B 每帧 float exact；
- Q4/Q8 temporal delta A/B 每个 transition float exact；
- 所有 ratio denominator 都是 finite 且大于零；
- 身份、进程、帧序、文件哈希与攻击测试全部通过。

全过只能得到 `TEMPORAL_DERIVATION_USABLE_FOR_THRESHOLD_FREEZE`。任何一项没过是 `DO_NOT_PROMOTE_TEMPORAL_DERIVATION`；合约或证据链错误是 `INVALID_EXPERIMENT`。

## 可证伪边界

这轮不会声明“无闪烁”“电影感”“人眼不可见”“Q8 时间质量等同 NATURAL”或“Q8 最优”。REFERENCE1024 只是代理；motion blur 关闭；只有一个场景、八帧、一台机器。正式 holdout 必须换一个不相交连续区间并重渲全部输出；主观结论必须由独立人类盲评给出。

## Freeze statement

在本协议与 spec 提交时，B33 renderer、runner、analyzer 尚不存在，`experiments/quadrature-temporal-derivation-v0-1/` 也尚未产生任何 B33 输出。
