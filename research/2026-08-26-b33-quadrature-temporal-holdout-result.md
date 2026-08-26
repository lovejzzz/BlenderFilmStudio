# B33 result · Q8 consecutive-frame temporal-proxy holdout

日期：2026-08-26（America/New_York）

正式判定：**`Q8_TEMPORAL_PROXY_HOLDOUT_SUPPORT`**

实验有效性：**true**（12/12 冻结攻击通过）

## 实际执行

协议与 SHA 先在提交 `f076c64` 冻结，正式工具随后在 `260a229` 实现。真实 Blender 5.2.0 LTS 对完全不相交的 frame `74–81` 完成：

- 28 个唯一 Blender PID；
- 224 次 render、224 个全新 scene-linear float32 EXR；
- 每个 cell-replicate 在单独进程内按升序连续渲染八帧；
- 7 个 transition × 3 个观察域；
- factory-startup analyzer 独立重跑 byte exact。

## 冻结门结果

四个 component verdict 全部通过：

- `REFERENCE_RELIABLE`：最大 reliability ratio `0.00118050`，门为 `≤0.05`；
- `Q4_Q8_TEMPORAL_EXACT_REPEATABILITY_SUPPORT`：Q4/Q8 frame composite 与 temporal delta A/B 全部 float exact；
- `Q8_NEAR_NATURAL_TEMPORAL_PROXY_SUPPORT`；
- `Q8_OVER_Q4_TEMPORAL_DOMINANCE_SUPPORT`。

所有 ratio denominator 都 finite 且大于零。

## 正式观察

| 域 | Q4 / NATURAL mean | Q4 max | Q8 / NATURAL mean | Q8 max / gate | Q8 / Q4 mean / gate | Q8 / Q4 max / gate |
|---|---:|---:|---:|---:|---:|---:|
| global | 1.31445 | 1.41563 | 0.82307 | 0.88559 / 1.00 | 0.62886 / 0.65 | 0.73856 / 0.75 |
| spatialEdgeUnion | 1.51270 | 1.66364 | 0.90225 | 0.98324 / 1.10 | 0.59998 / 0.65 | 0.72328 / 0.75 |
| referenceMotionTopK | 1.60608 | 1.77557 | 0.94965 | 1.03967 / 1.10 | 0.59504 / 0.65 | 0.72241 / 0.75 |

Q8 在七个 transition 的 global 与 spatial-edge 域全部低于 NATURAL32；在 motion 域只有 `75→76` 高于 NATURAL，ratio `1.03967`，仍在预注册 `1.10` 门内。Q4 在所有域的 mean 与 maximum 都高于 NATURAL32。

## 不能忽略的近门观察

正式数据比派生数据更接近失败边界：

- global Q8/Q4 mean `0.62886`，距离 `0.65` 仅 `0.02114`；
- transition `75→76` 的 global Q8/Q4 `0.73856`，距离 `0.75` 仅 `0.01144`；
- 同一 transition 的 motion Q8/NATURAL 从派生最大 `0.98847` 升到 `1.03967`。

因此结论不是“Q8 永远优于 NATURAL”，而是：在这个预注册的新连续区间与三域 proxy 下，Q8 保持在冻结 near-natural envelope 内，并通过了相对 Q4 的优势门。新样本显著消耗了预留余量，后续跨镜头复制很容易成为真正的反证机会。

## 成本

- NATURAL32：`2.670649 s`；
- Q4：`10.707780 s`，`4.0094×` NATURAL；
- Q8：`21.353905 s`，`7.9958×` NATURAL、`1.9942×` Q4；
- REFERENCE1024：`53.314518 s`，只用于实验 reference proxy。

## 非声明

这不是可见闪烁、人类偏好、motion blur、编码交付或电影感的证明。REFERENCE1024 mean 不是 ground truth；实验只有一个场景、八帧、一台机器、一个 Blender build，且 motion blur 关闭。Q8 布局和等权也未证明最优。

## 下一步

不应再在同一数值代理上无限复制。下一条高价值证据链是：生成包含 NATURAL/Q4/Q8 的匿名、随机化连续片段，冻结显示/播放器/观看距离和问题措辞，由独立人类完成盲评；同时把 B33 正式结果发布到研究网站，并把 near-boundary observation 作为醒目限制展示。

## 证据

- `experiments/quadrature-temporal-holdout-v0-1/results.json` · SHA-256 `e6728f75a224ba46f938ce21b2dbe03f44aa731d68f876abea40e78f03a81e44`
- `experiments/quadrature-temporal-holdout-v0-1/evidence/temporal-analysis.json` · SHA-256 `3f7a5204111a219eaec395055d7f44f8b4c94fbd49ab545142b817c060ea3534`
- `experiments/quadrature-temporal-holdout-v0-1/evidence/analysis-index.json` · SHA-256 `c4a4dfef00a7650337e2785906239306b9117282d513499cc5e57d8865cdef80`
- `experiments/quadrature-temporal-holdout-v0-1/evidence/analysis-binding.json` · SHA-256 `606c74e315b877ef9ccecd8dd273182bd75160805e020a533dab725dd7f239d8`
