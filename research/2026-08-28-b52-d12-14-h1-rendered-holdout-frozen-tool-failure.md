# B52-D12.14-H1：fresh rigid directional render holdout 的冻结工具失败

Date: 2026-08-28

Classification: `FORMAL_RUN_INVALIDATED_BY_FROZEN_ANALYZER_FAILURE`

Scientific verdict: **none**

## 摘要

H1 在预登记、tool freeze 与 14/14 official preflight 之后启动了唯一一次正式运行。12 个 Blender 5.2 Cycles CPU source renders、6 个 adapters、Python/Node 各 6 个 consumers，以及 Python/Node 各 12 个 typed envelopes 全部完成。第 55 个 child——冻结 analyzer——因 `KeyError: 'subdivisions'` 退出，runner 随之以 exit code 1 中止；audit、execution plan、result 与正式 receipt 均未产生。

这是工具链失败，不是对 Material-owner directional mechanism 的支持、方向失败或科学拒绝。相同 experiment ID 不得在修复后重跑。

## 冻结顺序

- Spec SHA-256: `7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8`
- Spec preregistration commit: `33692d211a37f6db98ddb3def4e91a4e5cd07547`
- Tool-freeze commit: `7488f0a44b4c158a5eeed5336992635fdca26400`
- Passing preflight commit: `5c6bacad87c9db72078ef4b7497d2da5bd929081`
- Formal root 在 runner 启动前不存在；runner 一次性创建该 root。

## 直接失败原因

Analyzer 的 mesh-identity gate 遍历 effective owners 并读取 `owner["subdivisions"]`。冻结 source、preflight 与 auditor 的 `effective_fixture` 会把全局 background subdivisions 展开到 background owner；冻结 analyzer 的同名函数只展开了 background size 与 transforms，遗漏 subdivisions。因此 analyzer 在处理第一个 source report 时中止：

```text
File "scripts/analyze-b52-d12-14-h1-rigid-directional.py", line 546, in main
    columns, rows = (int(value) for value in owner["subdivisions"])
KeyError: 'subdivisions'
```

Preflight 没有发现它，是因为 preflight 验证了 source probe 与自身 effective-fixture implementation，却没有用冻结 analyzer 读取 probe-shaped source report。下一实验必须新增 analyzer-on-probe-schema smoke，不能只分别测试 producer 与 checker。

## 已完成的正式 artifacts

失败发生前共有 54 个成功 children：

| Family | Count | Status |
|---|---:|---|
| Blender source processes / Cycles renders | 12 / 12 | completed |
| Adapter processes | 6 | completed |
| Python consumers | 6 | completed |
| Node consumers | 6 | completed |
| Python typed envelopes | 12 | completed |
| Node typed envelopes | 12 | completed |
| Analyzer | 1 attempt | failed |
| Audit | 0 | not started |

Partial root 在写入 failure record 前包含 354 files、约 33 MiB。12 个 source report 的 self-hash 与 EXR bindings、6 个 adapter reports 和 12 个 consumer reports 的 self-hash均有效。

## 非决定性事后取证

以下读取发生在 analyzer 已失败之后，只用于设计下一实验；它们不是 H1 formal verdict，也不能替代缺失的 analyzer/audit/receipt chain。

### 完整性与双实现

- Python/Node 每个 consumer array byte exact。
- 两次 repeat 的每个 adapter array byte exact。
- 两次 repeat 的每个 consumer array byte exact。
- 24 对 typed envelopes byte exact。
- 两次 repeat 的 EXR container bytes **不** exact，但解码后的 pass arrays exact。

对 TOP frame 0 的两个 EXR 进行 OpenImageIO metadata diff 后，Combined subimage 只有三个已观察差异：`Date`、`RenderTime`、`Scene`。其中 `Scene` 被 source 按 repeat 显式命名为 `..._R1` 与 `..._R2`；其他四个 subimages 没有 metadata 差异。冻结 analyzer 将 EXR file SHA 当作 source-repeat identity，因此即使修复 subdivisions bug，H1 的 hard-gate 仍会失败。下一实验应预登记并比较 canonical decoded source-pass digest（roster、channels、shape、dtype、pixel bytes），把 container metadata 单独报告；不能事后把 H1 的失败 gate 改义。

### Direction 与 quality 线索

| Cell family | Formal pass-derived directional witnesses | Eligible | Accepted | Acceptance | Quality max | Risk underbound RGB samples |
|---|---:|---:|---:|---:|---:|---:|
| TOP, each repeat | 189 | 189 | 189 | 100% | `2.4020671844482422e-5` | 0 |
| BOTTOM, each repeat | 189 | 189 | 189 | 100% | `1.9103288650512695e-5` | 0 |
| NEITHER, each repeat | 270 | 0 | 0 | n/a | n/a | 0 |

TOP/BOTTOM 的 targeted acceptance 与冻结 `2^-15` quality gate 在已完成 arrays 上均满足。NEITHER 的 zero acceptance 满足，但 formal witnesses 只有 270，低于预登记 minimum 1,024；如果完整 analyzer/audit chain 存在，这会触发 direction-failure branch，而不是 supported verdict。因为 H1 已先被冻结工具中止，这只能作为新实验 raster/denominator 设计的 pilot-informed 输入。

## H1 结论边界

H1 唯一合法状态是：

```text
FORMAL_RUN_INVALIDATED_BY_FROZEN_ANALYZER_FAILURE
scientificVerdict = null
same-ID rerun = forbidden
```

它不能修复 D12.12-H1，不能逆转 D12.13-D1，不能支持 threshold-only compiler promotion，也不能宣称 rigid directional mechanism 已被正式拒绝。唯一可复用的是：已披露的失败模式、decoded-array repeat identity、container metadata variation，以及 189/189/270 的事后取证计数。

## 下一实验的最低改进

新的 experiment ID 必须在任何修复工具或新 formal output 前预登记，并至少冻结：

1. analyzer/auditor/preflight 共用的 normalized fixture schema contract，但仍保持实现独立；
2. analyzer-on-probe-shaped report smoke，覆盖 background 与 foreground owners；
3. canonical decoded source-pass identity，另列允许变化的 EXR metadata，或明确保留 container-byte gate并预期失败；
4. 基于 H1 已披露 270 witnesses 的新 NEITHER raster/transform pilot，minimum 1,024 不得用事后放宽替代；
5. 新 tokens、render seed、signal coefficients、output root 与 attack mutations；
6. 失败也能写出 execution-failure receipt 的 runner finally-path。

Machine-readable failure record: `experiments/blender-material-owner-rigid-directional-render-holdout-v0-1/failure.json`.
