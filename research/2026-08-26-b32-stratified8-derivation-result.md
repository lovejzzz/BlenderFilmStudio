# B32.1 result · deterministic eight-point stratified jitter derivation

日期：2026-08-26（America/New_York）
状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`
判定：`PROMOTE_Q4_Q8_COST_CURVE_NEAR_NATURAL`

## 实际执行

按提前提交的 protocol，真实 Blender 5.2.0 LTS build `fbe6228777e7` 在 frame 37、72、103 上执行 8 个冻结 jitter point。A/B 每个 point 使用一个全新 PID，共 16 个 unique PID、48 次 EXR32 render。合成在 scene-linear RGB 中等权完成。

## 观察

| frame | NATURAL32 edge RMSE | Q4 edge RMSE | Q8 edge RMSE | Q8 / NATURAL | Q8 / Q4 | Q8 A/B RMSE |
|---|---:|---:|---:|---:|---:|---:|
| 37 | 0.01169878 | 0.01463431 | 0.01100687 | 0.9409× | 0.7521× | 0 |
| 72 | 0.01286223 | 0.01528887 | 0.01191050 | 0.9260× | 0.7790× | 0 |
| 103 | 0.01393324 | 0.01776561 | 0.01320555 | 0.9478× | 0.7433× | 0 |

Q8 的 mean Q8/Q4 edge ratio 为 `0.75816`，即在这三帧上将 Q4 edge-reference RMSE 再降低约 24.2%，每帧都优于 Q4。mean Q8/NATURAL edge ratio 为 `0.93821`，三帧均低于预写 `1.10` near-natural 门。mean Q8/NATURAL global ratio 为 `0.94546`。A/B 三帧全部 float exact。

实测 Q8 render seconds 为 8.8133，为已封存 Q4 的 `1.9545×`、NATURAL32 的 `7.9996×`。这一成本比例只覆盖 Blender render 计时，不是完整 pipeline 成本。

## 按冻结规则判定

- exact A/B 门：通过；
- 每帧不劣于 Q4：通过；
- mean Q8/Q4 不高于 `0.90`：通过，观察值 `0.75816`；
- 每帧 Q8/NATURAL 不高于 `1.10`：通过，最大值 `0.94777`。

因此按优先级得到 `PROMOTE_Q4_Q8_COST_CURVE_NEAR_NATURAL`。它的精确含义是：Q4 和 Q8 一起进入新 frame 的正式成本—质量 holdout，而不是 Q8 已经成为生产默认。

## 独立验证与攻击

新的 factory-startup Blender analyzer rerun 产生与封存 analysis byte-exact 的 SHA-256 `d4b9f35f…51469`。五个负向攻击全部被拒绝：

1. 非法 point `S9`；
2. 改写 frame 集为 `37/72/104`；
3. 非空 output directory；
4. 将冻结权重之一篡改为 `0.2`；
5. 制造重复 PID。

攻击验证了输入与证据边界，不会将 derivation 升级为 confirmation。

## 不能说

Q8/NATURAL ratio 低于 1 不等于“Q8 比 Blender 自然采样画质更好”。NATURAL1024 mean 只是 reference proxy；三帧已暴露于 derivation；没有 temporal sequence、human review、perceptual metric、motion blur 或完整镜头。这个数值可能反映该点集在当前 proxy 下的积分优势，也可能不能外推到新帧。

## 绑定

- result SHA：`518b4381656a8bd6fa5602523966a0da2ff69d25c6246be0836d0bb35ffc3c5a`；
- analysis SHA：`d4b9f35f3afad6fb9714119335ee55329de3f1207c84a0afa464deeccbd51469`；
- protocol SHA：`02f27aa777eceed56636c46aecffbe586f66cec980eed952500e686ca7d4aced`；
- renderer SHA：`77051a3840a217b793f47d1eb87bf77894bc95e04a7b1f14af58f054c99c3c77`；
- analyzer SHA：`c96e967393495cfdb999cf9114345bb524fcb5d0ec02fb285a15da83f11d0cf4`；
- runner SHA：`5d48e9d7b67ebfe08aec371a9acbe97fa5deb99c5e904eb612ceea4413736b11`。

Artifacts: `experiments/stratified8-derivation-v0-1/results.json`, `experiments/stratified8-derivation-v0-1/analysis.json`, `experiments/stratified8-derivation-v0-1/evidence/` and `research/2026-08-26-b32-stratified8-derivation-protocol.md`.
