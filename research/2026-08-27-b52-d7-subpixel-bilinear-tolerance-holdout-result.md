# B52-D7 · Subpixel Bilinear tolerance holdout result

- Date: 2026-08-27
- Runtime: Blender 5.2.0 LTS, build `fbe6228777e7`, Darwin arm64
- Preregistration commit: `bb68af37390ac4459e95ab78f17544446913c01f`
- Tool-freeze commit: `6d7c7b0933b40eb995facf940f15f7f1af988a3b`

## Verdict

`SUBPIXEL_BILINEAR_TOLERANCE_HOLDOUT_NOT_SUPPORTED`

First failed preregistered gate: `TOLERANCE_DISTRIBUTION`.

This result does not revise D6. Blender 5.2's CPU Displace Bilinear path is repeat-exact in the tested cells and remains below the pre-existing `1/65536` maximum-error boundary, but the unseen fixture family does not remain inside the separately frozen RMSE and p99 distribution bounds.

## Executed matrix

- six scalar Python reference processes;
- six independently coded Node reference processes;
- twelve fresh Blender processes, two per fixture;
- 24 unique child PIDs;
- twelve Blender compositor render calls;
- zero Cycles ray renders;
- zero source `.blend` files or external assets.

Every process exited zero without timeout. All six Python/Node reference pairs were byte-identical. All six Blender decoded repeat pairs were float32-array exact. Runtime identity, graph/RNA, source/displacement formulas, artifact hashes and operation counts all passed.

## Measurements

Frozen limits were maximum and alpha maximum ≤`1/65536`, RMSE and p99 ≤`1/1048576`, zero pixels above the maximum, and absolute signed mean per channel ≤`1/1048576`.

| Fixture | maximum | RMSE | p99 | distribution |
|---|---:|---:|---:|---|
| `LF_63X47_CLIP_Q1` | 3.635883e-6 | 2.096527e-7 | 5.364418e-7 | PASS |
| `LF_63X47_EXTEND_MIX` | 3.695488e-6 | 1.659994e-7 | 4.768372e-7 | PASS |
| `LF_63X47_REPEAT_FIELD` | 3.635883e-6 | 2.677278e-7 | 1.072884e-6 | FAIL p99 |
| `HF_127X73_CLIP_MIX` | 4.529953e-6 | 6.783242e-7 | 2.026558e-6 | FAIL p99 |
| `HF_127X73_EXTEND_MIX` | 7.629395e-6 | 1.007140e-6 | 3.695488e-6 | FAIL RMSE + p99 |
| `HF_127X73_REPEAT_FIELD` | 7.629395e-6 | 8.344341e-7 | 4.649162e-6 | FAIL p99 |

All six fixtures passed the maximum-error gate with zero pixels above `1/65536`. All six passed alpha maximum, signed bias and task sensitivity. Four of six failed p99; one of those also failed RMSE. The worst maximum error, `7.62939453125e-6`, is exactly half the maximum permitted magnitude, yet a small error spread across high-frequency samples is sufficient to fail the distribution contract.

The development smoke had predicted the same first failure before tool freeze. No threshold, fixture, arithmetic order or decision rule changed after that observation.

## Audit

The independent audit status is `PASS`. It matched:

- seven frozen tools and three D6 parent artifacts;
- Blender, bundled Python, Node and OCIO runtime identities;
- 24/24 run artifacts and self-hashed reports;
- 12/12 independently regenerated reference arrays;
- byte-exact analyzer replay and 24/24 diagnostic artifacts;
- all 23 adversarial failure routes;
- receipt, result and evidence-core self-hashes.

Audit `PASS` means the NOT SUPPORTED evidence is intact and replayable. It does not turn the failed scientific gate into support.

## Interpretation and next boundary

Measured fact: the Blender consumer is deterministic in this matrix, but its Bilinear arithmetic differs from the frozen external definition enough to violate the unseen distribution holdout on frequency and Repeat-heavy cases.

Inference, not proved cause: the pattern is consistent with internal filtering precision or operation-order differences. D7 does not identify the implementation cause.

A narrower low-frequency Clip/Extend subset passed, but it excludes the high-frequency boundaries that matter most for occlusion edges. The next experiment therefore should not promote that subset as the general temporal-warp primitive. The stronger route is a frozen external canonical warp consumer, followed by an explicit Raw float32 EXR bridge into Blender. Only after proving that bridge may a separate depth/layer-aware temporal accumulation experiment begin.

## Non-claims

- no support for Blender Displace as the general Bilinear production oracle;
- no revision of D6's bit-exact failure;
- no depth, occlusion, temporal integration or motion-blur validation;
- no claim about Vector passes, adaptive sampling or cinematic quality;
- no human perceptual evidence.

## Immutable evidence

- Receipt SHA-256: `beffa44928e9ea76c3ee5a792f3d484f5e89a6984fea7deb8d24efbf7894d004`
- Result file SHA-256: `c940d4a4205adbcf2068a395a65be683468d07ec5f4783bb8705b8315cfac6d2`
- Result canonical self-hash: `116e2a64bace01131cee6e0cbdb31952103e99a0cd49cdaf08dbbc5494a11fa5`
- Evidence-core hash: `9f3d4480156c7bd98907f2a1bfdba9542b12cbd9128fe93f2f5b7285a4745efd`
- Audit file SHA-256: `3f145d2878533ce640e2aab7d9be3cb0c7a5483cb4187ed76cff919740aedad1`
- Audit canonical self-hash: `d245b52fa2288ebceadb774e4759e8f05a1eff3ba0fab5b225c78b4e85c4ea9b`

Artifacts: `experiments/subpixel-bilinear-tolerance-holdout-v0-1/`.
