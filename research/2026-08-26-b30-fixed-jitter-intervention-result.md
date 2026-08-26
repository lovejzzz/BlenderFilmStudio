# B30 · natural versus CENTER fixed-jitter intervention result

日期：2026-08-26（America/New_York）  
预注册提交：`82de95c`  
正式工具提交：`227e7b3`  
冻结判定：`FIXED_JITTER_STRICT_STABILITY_SUPPORT`

## 正式执行

严格按冻结 schedule `N01,C01,…,N12,C12` 启动 24 个全新 Blender PID。NATURAL 与 CENTER 各 12 个进程，每个进程只设置一次 frame 38并连续 render 12 次；共 288 次真实 Blender render、288 个 PNG。全部 PID 唯一，25/25 个预注册攻击达到预期拒绝 reason。

NATURAL 确保 source scene 不含 `override_pixel_jitter_sample`；CENTER 在首次 render 前设为 `[0.0,0.0]`。所有进程使用同一冻结 `.blend`、BuildPlan、structure、ReviewRenderSpec、Blender 5.2.0 LTS binary、ACES 2 OCIO、Eevee 32 samples、dither 0、Fast GI、TAA reprojection 与 FIXED/8 threads。源 `.blend` 没有保存。

## 主结果

CENTER 的 12/12 PID、144/144 renders 全部命中 derivation 之前冻结的 decoded RGB SHA `ba0591ae97f08f72be2558ebfcbd17ac894a4ea76256b03bae3dea4215ff8aca`。没有 CENTER novel hash，也没有 cell 内 transition。

NATURAL active control 在 10/12 PID 内同时出现两个冻结 mode，超过预注册 ≥2 PID 门槛：

- NATURAL REFERENCE：125/144；
- NATURAL ALTERNATE：19/144；
- switching PID：10/12；
- adjacent mode transitions：30/132，REFERENCE→ALTERNATE 15、ALTERNATE→REFERENCE 15；
- NATURAL novel hash：0。

N01 与 N09 各自 12/12 REFERENCE；其余十个 NATURAL PID 都切换。CENTER 与 NATURAL 合计 264 个 within-PID adjacent comparisons。

因此按冻结 precedence，正式 decision 是 `FIXED_JITTER_STRICT_STABILITY_SUPPORT`。结果支持：在本机器、本 Blender build、本 scene/frame/profile 下，CENTER intervention 与一个跨 12 个独立进程、144 次调用的严格 decoded identity 相容；自然对照同时证明确实存在本实验意图干预的 within-PID mode switching。

## 独立结果审计

正式 classifier 在新的 factory-startup Blender 进程中对同一冻结 index 独立重跑，输出 SHA 与晋级 classification 完全一致：`95c7b5ab7b735c101e5392d7fc775ddb7462896b18761e324ebe6dc3e6f03749`。正式 result SHA 为 `a25be579e1bc4c958962141a32e1b5e50c6cf32a3e352dad5c0d1d71e354e73f`；classification binding SHA 为 `23cadce3dc45c6c58a68c909e8896260fc39f60bef676889a5071834734577a7`。

## 代价与结论边界

这个支持结果不能被写成“修好了 17 个像素”。在正式实验之前冻结的 derivation 已测得 CENTER 相对 NATURAL REFERENCE 改变全幅 131,779 / 518,400 个 decoded pixels，最大 46 PNG code values，normalized RMS `0.0036968892`。CENTER 锁定的是另一套采样结果。

它也没有单独证明 filter U/V jitter 是根因：Blender 5.2 源码显示该 hidden property 还以 raw values 派生 time、closure 与 raytrace-X 等 sample dimensions。干预有效只说明这组联动足以消除本 profile 中观测到的模式变化。

不能据此主张 CENTER 抗锯齿更好、时间连续性更好、感知上不可见、电影感更强或适合生产默认值。B26 human review 保持 `PENDING`；EXR mastering 也未被本 PNG strict-identity 实验替代。

## 下一边界

下一步必须把“稳定性收益”与“采样质量代价”分开验证。应先用真实 Blender 派生一个不含 B30 holdout frame 的高 sample / spatially supersampled reference 与边缘 ROI，再预注册 NATURAL、CENTER 和参考图之间的静态 aliasing、scene-linear error 与时序残差 holdout。质量阈值与 human review 不能在看见正式结果后选择。

Artifacts: `experiments/fixed-jitter-intervention-v0-1/results.json`, `experiments/fixed-jitter-intervention-v0-1/evidence/`, `specs/fixed-jitter-intervention-spec.v0.1.json` and `research/2026-08-26-b30-fixed-jitter-intervention-protocol.md`.
