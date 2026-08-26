# B33 result · deterministic quadrature temporal-error derivation

日期：2026-08-26（America/New_York）

状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`

派生判定：**`TEMPORAL_DERIVATION_USABLE_FOR_THRESHOLD_FREEZE`**

## 实际执行

冻结协议之后才实现 renderer、analyzer 与 runner。真实 Blender 5.2.0 LTS 在 frame `121–128` 上完成：

- 28 个唯一 Blender PID；
- 224 次真实 render、224 个全新 float32 ZIP EXR；
- 每个 cell-replicate 在一个新进程内按升序连续渲染八帧；
- 10/10 负向攻击按预期拒绝；
- factory-startup analyzer 独立重跑与接受结果 byte exact。

REFERENCE1024 A/B temporal residual 相对 NATURAL32 的最大 reliability ratio 为 `0.00794548`，低于冻结的 `0.10` 派生有效性门。Q4/Q8 composite A/B 在八帧上 float exact，Q4/Q8 temporal delta A/B 在七个 transition、三个观察域上也全部 float exact。所有 ratio denominator 均 finite 且大于零。

## 主要观察

| 域 | Q4 / NATURAL mean | Q4 max | Q8 / NATURAL mean | Q8 max | Q8 / Q4 mean | Q8 / Q4 max |
|---|---:|---:|---:|---:|---:|---:|
| global | 1.43399 | 1.49316 | 0.81768 | 0.83436 | 0.57036 | 0.58030 |
| spatialEdgeUnion | 1.72114 | 1.80903 | 0.90527 | 0.94248 | 0.52613 | 0.53648 |
| referenceMotionTopK | 1.82309 | 1.93421 | 0.94804 | 0.98847 | 0.52021 | 0.53057 |

在这段派生区间里，Q4 的 temporal error delta 明显高于 NATURAL32，尤其在参考移动区域；Q8 则在七个 transition 的三个域里全部低于 NATURAL32。Q8 的 temporal RMSE 约为 Q4 的 `0.52–0.57×`。这与 B32 单帧 proxy 中 Q8 优于 Q4 的方向一致，但尚未构成时间质量确认。

## 成本

Blender 自报 render timer 合计：

- NATURAL32：`2.689942 s`；
- Q4：`10.720159 s`，即 `3.9853×` NATURAL；
- Q8：`21.541101 s`，即 `8.0080×` NATURAL、`2.0094×` Q4；
- REFERENCE1024：`53.210330 s`，只作为实验 proxy，不是候选生产成本。

## 解释与反例边界

这是阈值派生，不是正式 holdout。尤其不能把“Q8/NATURAL ratio < 1”翻译为“Q8 肉眼更好”或“电影感更强”。误差代理依赖 dual-REFERENCE1024 mean；motion blur 关闭；只有一个场景、八帧、一台机器；固定点集也可能在其他运动、材质、透明、毛发或体积场景失效。

Q4 是一个重要负向观察：四倍成本并没有自动换来更好的 temporal proxy。正式协议因此不应把 Q4 预设为 near-natural，而应检验 Q8 是否在不相交的连续区间保持 near-natural，并继续记录 Q4 作为成本曲线的中间点。

## 下一步冻结原则

正式 B33 holdout 必须：

1. 使用与 `121–128` 不相交的连续八帧；
2. 重渲全部 224 个输出，不复用本轮 EXR；
3. 保持三个观察域、exact-top-k total order 与 exact-repeatability 门；
4. 在任何正式工具或输出之前冻结 Q8/NATURAL 与 Q8/Q4 阈值；
5. 仍不替代独立人类盲评。

## 证据

- `experiments/quadrature-temporal-derivation-v0-1/results.json` · SHA-256 `78f71f8ae38f8e5ed07dd21611e995a5be4a1870b2bf2ea4316c35c709b720ff`
- `experiments/quadrature-temporal-derivation-v0-1/evidence/temporal-analysis.json` · SHA-256 `e79518fdb53e24371444cdbd80057bbd5e4d092f68fa6ab193f5ef345a982c40`
- `experiments/quadrature-temporal-derivation-v0-1/evidence/analysis-index.json` · SHA-256 `67969850ea431971e18832d61d0f0dbaedda7b809bd7cd97d334c24d4d49f1af`
- `experiments/quadrature-temporal-derivation-v0-1/evidence/analysis-binding.json` · SHA-256 `383391568f1ba1c6ed502af1a0627614f9551a57d0a93b85bb743ceda6d6a144`
