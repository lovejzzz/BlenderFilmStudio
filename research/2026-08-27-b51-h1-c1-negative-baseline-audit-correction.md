# B51-H1-C1：负基线攻击隔离修正

日期：2026-08-27  
范围：分析与审计，不重新渲染

## 首次结果

13 个 Blender 进程全部完成，canary 通过，但正式 H1 门为负。首次分析输出保留为：

- `experiments/native-metal-production-holdout-v0-1/results.initial-v0.1.json`

它正确保留了像素与阈值结论，但攻击计数仅为 `18/21`。原因不是三个攻击未被识别，而是实际证据已经触发 `EXACT_PASS_DOMAIN`；在该负基线上再注入位于其后的攻击时，验证器仍先返回原失败，遮蔽了后续攻击。

## 允许的修正

1. 每个攻击从同一份证据的隔离副本开始。
2. 隔离副本只把实际失败的 promotion metrics 临时归零、exact-pass 布尔量临时设为真、timing 临时设为零，以构造可到达每一道验证分支的攻击基线。
3. 正式证据、EXR、receipt、预注册阈值、实际 `baseFailure` 与最终 `NOT_SUPPORTED` verdict 不变。
4. 审计器允许 `SUPPORTED + baseFailure=null` 或 `NOT_SUPPORTED + baseFailure!=null` 两种自洽结果被判为有效证据；审计通过不等于 promotion 通过。

修正后的审计仍验证初始 tool-freeze commit 中四个工具的 Git blob，并从原始 receipt 与 EXR byte-exact 重放结果。
