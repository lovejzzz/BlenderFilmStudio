# B32 formal holdout attempt 1 · invalid edge-mask contract

日期：2026-08-26（America/New_York）
状态：`FORMAL_ATTEMPT_INVALID_BEFORE_METRIC_DECISION`
判定：`IDENTITY_OR_DESIGN_INVALID`

## 发生了什么

按 spec SHA `e2a66a17…0b51d` 启动的第一次正式运行已完成 28 个 unique Blender PID、112 次 EXR32 render、28 份 manifest、28 份 render report 和 28 份 thread report。但 analyzer 在计算第一帧的候选误差前主动终止：

`BFS_B32_HOLDOUT_ANALYZE_ERROR Frame 22 edge pixel count mismatch`

预注册 spec 同时规定“dual-reference gradient 的 top 5%”和“exactly 25,920 pixels”，但工具实现是 NumPy 95% quantile 后使用 `magnitude >= threshold`。frame 22 在 cutoff 上恰好有两个相等梯度值：

- `>` threshold：25,919 pixels；
- `==` threshold：2 pixels；
- `>=` threshold：25,921 pixels；
- 预写 exact target：25,920 pixels。

frames 59、97、136 没有 cutoff tie，但只需一帧违约就使整次 formal attempt invalid。

## 为什么不能直接改一行再继续

将 `>=` 改成 `>` 会得到 25,919，仍不是 exact top 5%；保留 `>=` 会得到 25,921。事后选其一会改变已冻结的 mask，而且这次 runner 还没有完成 analysis binding 和 negative attacks。因此 attempt 1 没有任何 quality verdict，已完成的渲染也不能被重贴标签为干净的 confirmation。

这是一个分析合约的反例，不是 Q4/Q8 质量的支持或反驳。

## 修正原则

新的 v0.2 协议必须在任何 v0.2 analysis 前明确一个 total order，例如按 `(gradient magnitude descending, flattened pixel index ascending)` 稳定排序后精确选前 25,920 个。这个规则会在 tie 时决定选哪个 pixel，必须被当成新协议，而不是 v0.1 的“bug fix 后继续”。

## 证据

- invalid result SHA：`7455bfa65783596ab922f01520812feb5cfbfa08abeb1d769a753e2259f813a8`；
- tie diagnostic SHA：`722759c3b5084fe786c08eb0c348fcc0ee6a351a60250e086aeace5c0f4f4d80`；
- process ledger SHA：`7f8c20053bfb338563e612587fcd924dce27af2066bd1ec93a1616f87e164005`；
- analysis index SHA：`f800a8454e335c4e7fe18448f2e0008c0255bf14c4125e77177814738f1626a6`。

Artifacts: `experiments/quadrature-cost-holdout-v0-1/results.json`, `experiments/quadrature-cost-holdout-v0-1/evidence/edge-mask-tie-diagnostic.json`, `experiments/quadrature-cost-holdout-v0-1/evidence/process-ledger.json` and `experiments/quadrature-cost-holdout-v0-1/evidence/analysis-index.json`.
