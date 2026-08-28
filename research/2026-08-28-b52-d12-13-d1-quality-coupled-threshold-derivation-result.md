# B52-D12.13-D1：quality-coupled Q30 threshold derivation 结果

Date: 2026-08-28  
Classification: post-hoc derivation, not a fresh holdout  
Verdict: `MATERIAL_OWNER_QUALITY_COUPLED_THRESHOLD_CANDIDATE_NOT_DERIVED`

## 研究问题

D12.12-H1 证明 `131072 Q30` risk threshold 与 `32768 Q30` quality gate 不闭合：risk 虽然仍是实际 RGB error 的上界，但 threshold 是 quality gate 的四倍，因此会接受真实误差超标的 cell。本 derivation 只读取不可变 H1 arrays，测试把全局 threshold 收紧到 `32768 / 24576 / 16384 / 8192 / 4096 Q30` 能否同时满足：

- accepted RGB maximum 与 RMSE 不超过 `3.0517578125e-5`；
- risk underbound、invalid-history accept 与 Material alias 均为 0；
- 四个 primary fixtures 的 accepted/radius-2 coverage 均不低于 0.97；
- primary fixtures 内每个 Material owner retention 均不低于 0.95；
- static、fallback、repeat、cross-language、process 与 evidence-chain gates 全部通过。

不能通过 coverage 的安全 threshold 不得被导出，也不能事后改变 frozen threshold family。

## 方法与证据完整性

独立 Python 与 Node consumers 对六个 fixtures、两个 repeats、五个 thresholds 分别产生 accepted 与 reconstructed arrays；第三 analyzer 重算 acceptance、quality、coverage 与 owner retention。完整 matrix 使用 26 个唯一子进程：12 Python、12 Node、1 analyzer、1 independent auditor；全部 exit 0。没有 Blender render、model 或 network call。

Analyzer hard checks 19/19；auditor baseline 19/19，覆盖九个必需攻击族的 concrete semantic attacks 88/88。Evidence receipt 有效。Python/Node every-array、两个 repeats 与 fallback 全部 byte exact；immutable H1 risk underbound count 仍为 0。

第一次 run 的 analyzer 已形成相同科学结论，但 auditor 为 87/88：mutation tool 在循环结束后误取 STATIC payload，使 `FALLBACK_FROM_H1` 没有真正产生变异。该 attempt 完整保存在 `experiments/blender-material-owner-quality-coupling-derivation-v0-1-attempt0-audit-tool-bug/`，没有 evidence receipt。Commit `bbc8192` 只把 witness 绑定到预先固定的非静态 LEFT/R1 cell；threshold、gate、input、metric 与 verdict 均未改变。修复后 rerun 的全部科学 metrics 与 attempt 0 一致。

## 结果

| Threshold Q30 | Accepted RGB max | RGB RMSE | 最低 primary cell coverage | 最低 primary owner retention | Verdict |
|---:|---:|---:|---:|---:|---|
| 32768 | 7.5101852e-6 | 2.6663717e-6 | 0.647291 | 0.534076 | reject |
| 24576 | 5.6028366e-6 | 1.8582055e-6 | 0.524661 | 0.372083 | reject |
| 16384 | 3.7550926e-6 | 1.1042582e-6 | 0.429636 | 0.246557 | reject |
| 8192 | 1.8477440e-6 | 3.9639875e-7 | 0.310626 | 0.089346 | reject |
| 4096 | 9.2387199e-7 | 1.3126201e-7 | 0.268381 | 0.033540 | reject |

五档 threshold 的 quality/safety gates 全部通过，但每一档都同时失败 `PRIMARY_CELL_COVERAGE` 与 `PRIMARY_OWNER_RETENTION`。最宽松的 `32768 Q30` 已将 global accepted maximum 压到 quality gate 的约 24.6%，仍只保留 BOTTOM fixture 的 64.7% radius-2 cells；BOTTOM occluder owner retention 只有 53.4%。LEFT/RIGHT/TOP/BOTTOM 在 R1 的 cell coverage 分别为 80.9% / 84.2% / 71.3% / 64.7%。NEITHER negative-control fixture 在全部五档均 accepted=0；STATIC control 在全部五档保持 14591/14591。

## 可证伪结论

H1 的 risk 数值对 quality gate 明显过于保守。简单把一个全局 acceptance threshold 降到 quality gate 或更低，确实消除了已观察的质量违例，但不能保住覆盖率；因此“只调 threshold”不是可行修复。此结论拒绝一个机制，不拒绝 risk upper bound 本身，也不证明不存在更好的结构化 policy。

下一步应把问题拆成两个独立实验：

1. 修复 TOP/BOTTOM/NEITHER fixture geometry，使 directional stress domain 在 render 前通过 zero-render oracle 校准；
2. 预登记 risk tightness decomposition，按 full-stencil / one-sided support 与 Material owner 报告 `risk / realized-error` envelope，研究可证明安全的 tighter bound 或多级 policy。任何新 policy 必须在新鲜 Blender 5.2 holdout 上同时通过 quality 与原 coverage gates，不能用本 post-hoc arrays 直接提升。

## 证据身份

- Result file SHA-256: `66a1598e2b4f0dee1ee7773b566c1bf5085a2a02fc911e050b873bdcfa28ca19`
- Result self-hash: `c0e43d0acac844939457f0fdec0b8eda7fa850d0fed26720b873401aa88a4737`
- Audit file SHA-256: `cc761d726c409d54cbf84faa07a7a600e35a2ab5d65e58dadee50fb9f6d0d988`
- Audit self-hash: `fcbd74e2ae5b2dc62e226b24b58c45b2c5753c35aff1058829055f0445f6579a`
- Execution file SHA-256: `206b69e5e2ba9d52d79b6dcd709a88f5c62a0683766173c970b4fd7dd0cf8009`
- Execution self-hash: `8bca7f38c5907d9097691db443ab943bfc074b705b92405a40554226ebdd4545`
- Receipt file SHA-256: `a7448121ef15947edd2beed24f2222792672b43a06afcd67e7807b68d10c0caa`
- Receipt self-hash: `984ed1922979face344d6d387a835bc565f5c69d9519c8c88d83f544e16703f2`
