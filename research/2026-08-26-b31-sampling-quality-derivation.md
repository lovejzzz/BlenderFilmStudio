# B31 derivation · fixed-jitter scene-linear quality cost

日期：2026-08-26（America/New_York）  
状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`

## 为什么 B30 之后必须做这一层

B30 确认 CENTER `[0,0]` 在本 profile 上 144/144 decoded RGB strict exact，但 derivation 同时显示它相对自然输出改变全幅 131,779 个像素。严格稳定本身不能回答固定单一 sample position 是否损害子像素积分与边缘质量。

B31 derivation 因此不再测“是否 exact”，而测 NATURAL32 与 CENTER32 相对一个高 sample scene-linear reference proxy 的数值误差。它仍不是感知质量或电影感实验。

## 参考代理与性能边界

最初真实 Blender 性能 pilot 测试了 1920×1080、256 samples 的 2× spatial proxy：单帧约 73.61 秒。该成本会使双参考、多 frame、正式 holdout 过重，因此没有把它偷偷降级后仍称“空间超采样”。

接受的 derivation 使用原始 960×540 分辨率、NATURAL 1024 samples 的两个独立 Blender PID；逐像素平均 A/B 得到 reference proxy。它明确记录 `spatialSupersampling=false`、`truthClaim=false`。另有 NATURAL32 A/B 与 CENTER32 A/B，共六个全新 PID，在未使用 frame 37、72、103 上输出 EXR32 scene-linear RGBA；总计 18 次 render。

edge ROI 的规则在 analyzer 输出前写定：对双参考均值的 RGB Euclidean central-difference magnitude 取 top 5%。每帧恰有 25,920 / 518,400 个 edge pixels。主探索量是 CENTER32 与 NATURAL32 相对 reference proxy 的 edge RMSE ratio。

## 观察

双 1024-sample reference agreement 极高：frame 37 与 103 float exact；frame 72 的全局 A/B RMSE `0.00000126496`、edge RMSE `0.00000565705`。相比之下，32-sample 候选的 edge RMSE 在 `0.0117–0.0315` 数量级，所以 reference disagreement 远小于候选误差。

CENTER32 / NATURAL32 RMSE ratio：

| frame | global | edge top 5% | non-edge |
|---|---:|---:|---:|
| 37 | 1.4673× | 2.2360× | 1.0826× |
| 72 | 1.4211× | 2.1876× | 1.0750× |
| 103 | 1.4215× | 2.2623× | 1.0933× |
| mean | 1.4366× | 2.2286× | 1.0836× |

三帧方向一致：CENTER 的最大相对代价集中在由参考代理定义的高梯度 ROI，而非非边缘区。这与固定 pixel jitter 改变子像素采样的工程预期相容，但不能单凭这一结果命名为人眼可见 aliasing。

NATURAL32 A/B 在 frame 37、72 exact；frame 103 全局 RMSE 约 `0.00001064`。CENTER32 A/B 三帧全都 float exact。它再次显示 repeatability 与 reference error 是不同维度：CENTER 更可重复，同时离高 sample proxy 更远。

## 能说与不能说

可以说：三个 derivation frame 都把 CENTER32 的 edge-reference RMSE 放在 NATURAL32 的 2.18× 以上；双 1024 reference 的自身差异远小于候选误差，足以提名一个未见 frame holdout。

不能说：1024-sample 均值是真值，CENTER 的画面肉眼更差，2.2× 数值误差等于 2.2× 可见损失，或这个比例能外推到其他场景/引擎/GPU。没有空间超采样，没有 temporal sequence，也没有人类评审。

## 下一冻结候选

正式 holdout 应在未见 frame 10、44、86、120 上重复两个 NATURAL32、两个 CENTER32 与两个 NATURAL1024 PID。参考可靠性门可冻结为每帧 reference A/B edge RMSE 不超过 NATURAL32 mean edge RMSE 的 5%；质量代价支持门可保守冻结为所有四个 frame 的 CENTER/NATURAL edge RMSE ratio ≥1.5。1.5 是从 derivation 最小值 2.1876 向零效应方向收缩的未见帧门，不得在 holdout 后修改。

- derivation result SHA：`a775834339deccf86d6fa536e2cf97a639f63b8ef2474de647e088231fbcda64`；
- analysis SHA：`b7466732975b7a400e5152b1c734898e5666423df6337e743b2972cecdb206cf`；
- renderer SHA：`fe3a28a6bfd75dd7f9c0b89c29e7cb7e0b1c8afdbbb51a0c40117a00656536e1`；
- analyzer SHA：`bced5a658ffa84e7ccfd0a95a8db205e2950d9600f53684b669130a6684f70ef`。

Artifacts: `experiments/sampling-quality-derivation-v0-1/results.json`, `experiments/sampling-quality-derivation-v0-1/analysis.json`, `experiments/sampling-quality-derivation-v0-1/evidence/`, `blender/render_b31_sampling_quality_derivation.py` and `blender/analyze_b31_sampling_quality_derivation.py`.
