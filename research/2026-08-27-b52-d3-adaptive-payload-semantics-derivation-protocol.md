# B52-D3：adaptive payload task-semantics 派生协议

日期：2026-08-27

状态：`PREREGISTERED · ZERO RERENDER`

## 问题

B52-D2 证明更宽松 adaptive threshold 能显著降低 samples 与 render time，但所有 48 个 candidate cells 的 Cryptomatte、Normal、Vector 完整 payload 门均失败。Depth 反而 48/48 通过并在冻结域内保持零差异。

D3 不允许把“non-exact”直接改写成“可接受”，也不允许把看到过的 D2 数据重新包装成 holdout。它只回答：这些差异在明确的 compositor / stable-surface 任务域中位于哪里、大小多少，能否形成下一次 fresh-seed holdout 的候选语义。

## 输入冻结

- 父输入是 D2 spec、54-run receipt、valid-negative result 与 PASS audit 的精确 SHA-256；
- 必须重新核对 54/54 EXR 身份与八个 subimage roster；
- 必须先复核 18/18 profile × variant 三重复 decoded exact，随后才允许只分析 repeat 1；
- 分析 8 profiles × 2 variants = 16 个 candidate–baseline pair；
- Blender processes=0、renders=0、网络与模型调用=0。

## 空间域

所有 pass 共用一个只由 baseline 构造的区域合同，避免 candidate-dependent masking：

1. Depth 小于 `1e9` 为 foreground；
2. baseline rank-0 Cryptomatte coverage ≥0.999 为 confident dominant；
3. foreground 中四邻域 dominant ID 改变，或任何可见对象 baseline matte 的 alpha 严格位于 0–1，构成 boundary seed；
4. seed 做一像素 Chebyshev dilation；
5. `stableInterior = foreground ∩ confident dominant ∩ boundary 外部`。

## Cryptomatte 任务

按 Cryptomatte 1.2.0 manifest 解码六组 ranked ID/coverage。对每个 baseline 可见对象分别测 hard matte mismatch、stable-interior mismatch、alpha p50/p95/p99/max/RMSE 与 changed-alpha 的边界局部化比例。

同时运行两个确定性 unit-contrast matte composite：白前景/黑背景与红前景/黑背景。它们不是审美合成，只把 alpha error 映射到明确 RGB 输出。

派生分类器冻结为：stable-interior hard mismatch=0、stable-interior confident dominant mismatch=0、changed alpha 至少 95% 位于 boundary、composite p99≤1/255、max≤0.05。通过只表示“值得 fresh holdout”，不表示生产安全。

## Normal 任务

在 stableInterior 内归一化 XYZ，测有效向量 mask mismatch 与角度误差 p50/p95/p99/max。再用五个固定半球方向计算 Lambertian `max(dot(n,l),0)` 探针。

候选分类器：mask mismatch=0、角度 p99≤0.25°、max≤2°、Lambertian p99≤1/1024、max≤1/255，并且 changed normal 至少 95% 边界局部化。

这些是工程派生阈值，不是人类感知阈值。

## Vector 任务

官方文档把 Vector 定义为供 Vector Blur 使用的 motion vectors。D3 把 X/Y 与 Z/W 作为两个二维 endpoint pair，但不推断哪一组代表 previous 或 next。它在 stableInterior 测两个 pair 的 endpoint error 分布、nonzero-support mismatch 与边界局部化。

候选分类器：stable-interior support mismatch=0、两个 pair 的 p99≤1/1024、max≤1/64，并且 changed vector 至少 95% 边界局部化。D3 不运行 Vector Blur，也不主张 temporal equivalence。

## 可视诊断

为三个预先指定的代表 profile——最温和 `0.015/min0`、第一个双场景成本过门 `0.02/min32`、最高 savings `0.05/min32`——在两个构图各输出 Crypto maximum-alpha、Normal angle、Vector maximum-pair-error 三张 map，共 18 张 PNG。

映射不能在看过派生结果后自动伸缩：Crypto 固定裁剪到 `[0, 0.05]`，Normal 固定裁剪到 `[0, 2°]`，Vector 固定裁剪到 `[0, 1/64]`。令归一化值为 `t`，RGB8 固定编码为 `(t, t², 0)`。每张 canonical JSON sidecar 绑定 map kind、candidate/baseline identity、映射合同、decoded-value SHA-256 与 PNG SHA-256。

## 判定

只要父身份、54 artifacts、repeat identity、16-pair measurement、18 PNG、13 attacks、operation boundary 与独立 replay 全部成立，D3 就可判 `ADAPTIVE_PAYLOAD_SEMANTICS_DERIVATION_USABLE`；没有 profile 通过三类 classifier 仍可得到有效结果。

任何 future holdout candidate 都只是下一实验的预注册输入。D2 的 `NOT_SUPPORTED` 永不改变；INTERIOR beauty 也仍是独立阻断门。

机器预注册：`specs/adaptive-payload-semantics-derivation.v0.1.json`
