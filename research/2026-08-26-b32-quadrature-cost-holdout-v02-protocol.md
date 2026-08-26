# B32 formal protocol v0.2 · exact-top-k quadrature cost–quality holdout

日期：2026-08-26（America/New_York）
状态：`PREREGISTERED_BEFORE_V02_TOOLING_OR_OUTPUTS`

## 为什么必须有 v0.2

v0.1 完成 28 个正式渲染 PID 后，在分析第一帧时因 edge-mask cutoff tie 终止。预写合约要求 exactly 25,920 pixels，而 quantile + `>=` 在 frame 22 选出 25,921。v0.1 已封存为 `IDENTITY_OR_DESIGN_INVALID`，不产生任何 Q4/Q8 quality verdict。

v0.2 不复用 v0.1 输出，也不复用 v0.1 四帧。主协议为 `specs/quadrature-cost-holdout-spec.v0.2.json`，最终 SHA-256 为 `4f56bde9d9037bbeb2e508d4d5880c0141c625bb20d37aea439812a1599b3b21`，在任何 v0.2 tooling/output 之前写入本文并提交。

## 冻结的新 mask 规则

每帧仍使用 dual-NATURAL1024 mean 的 RGB Euclidean central-difference gradient magnitude，但不再使用 quantile threshold 产生 mask：

1. 将 540×960 gradient magnitude 以 C row-major 顺序展平；
2. 按 magnitude 降序排序；
3. magnitude 相同时，按 flattened pixel index 升序；
4. 精确选前 25,920 个 index。

实现等价于 `np.lexsort((indices, -flat_magnitude))[:25920]`。这个 total order 对 tie 也给出唯一 mask，每帧 cardinality 必须精确为 25,920。

## 新帧与执行

- holdout frames：`31, 67, 109, 143`；
- v0.1 frames `22,59,97,136` 以及更早 B31/B32 frames 全部排除；
- NATURAL32 A/B：2 PID、8 renders；
- NATURAL1024 A/B：2 PID、8 renders；
- Q4 A/B：8 PID、32 renders；
- Q8 A/B：16 PID、64 renders；
- 总计 28 个全新 unique PID、112 renders，从空 v0.2 work/evidence 目录开始。

## 判定门槛保持不变

v0.2 只修复 mask total-order 定义并更换帧，不放宽质量门：

- reference reliability ratio 每帧 `<= 0.05`；
- Q4/Q8 composite A/B 每帧 float exact；
- Q4/NATURAL edge ratio 每帧 `<= 1.40`；
- Q8/NATURAL edge ratio 每帧 `<= 1.10`；
- Q8/Q4 每帧 `<= 1.0`，mean `<= 0.90`。

五项都通过才是 `COST_QUALITY_CURVE_SUPPORT`，否则是 `COST_QUALITY_CURVE_PARTIAL_OR_FAILURE`并保留 component failures。

## 非声明

v0.2 通过也仅支持新四帧上的 scene-linear reference-proxy 成本—质量曲线，不是可见质量、temporal stability、motion blur、human preference、电影感或点集最优性的证明。
