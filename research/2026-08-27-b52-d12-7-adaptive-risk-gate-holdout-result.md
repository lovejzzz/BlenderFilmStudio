# B52-D12.7 · Adaptive local-risk gate fresh holdout result

Date: 2026-08-27

Frozen verdict: `ADAPTIVE_GATE_WITHIN_TOLERANCE_BUT_STRESS_OR_COVERAGE_NOT_SUPPORTED`

Corrected audit: `PASS · 30/30 repaired-self-hash mutations rejected`

## Conclusion

The adaptive candidate passed every candidate-specific gate on all three unseen static Blender fixtures. It retained 99.60%–99.86% of the radius-2 domain, rejected a non-empty high-risk tail in every primary fixture, preserved at least 95% of every registered owner's radius-2 pixels, and retained 10.47%–26.70% more total pixels than global radius 3. Its RGB maximum stayed below the frozen half-gate and the local risk bound underestimated zero RGB samples.

The frozen overall verdict is nevertheless bounded rather than supported. The only false analyzer check was `RADIUS3_PRODUCTION`: the paired radius-3 comparator reached `2.1457672119140625e-6` on the frustum/crossbar/sphere fixture, above the unchanged production maximum `1.9073486328125e-6`. The adaptive candidate on that same cell stayed at `8.940696716308594e-7`, below the twofold-headroom limit `9.5367431640625e-7`.

This distinction is important. D12.7 is evidence that the frozen adaptive rule is better than global radius 3 on these fresh static fixtures; it is not a formal promotion, because the preregistered analyzer required every recorded check—including comparator production—to pass for the supported verdict.

## Primary-repeat measurements

| Fixture | radius 2 | adaptive | rejected | radius 3 | adaptive / radius 2 | adaptive / radius 3 | adaptive RGB max | radius-3 RGB max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ripple + rounded box | 7,661 | 7,650 | 11 | 6,925 | 99.856% | 110.469% | `8.34465e-7` | `1.25170e-6` |
| Superellipse + torus | 4,325 | 4,318 | 7 | 3,408 | 99.838% | 126.702% | `8.34465e-7` | `1.60933e-6` |
| Sphere + frustum + crossbar | 6,472 | 6,446 | 26 | 5,736 | 99.598% | 112.378% | `8.94070e-7` | `2.14577e-6` |

Across primary cells the adaptive rule rejected 44 radius-2 pixels. Every registered owner retained at least its radius-3 count; the lowest per-owner radius-2 retention was 95.963% on the crossbar, still above the frozen 95% gate. All six repeat cells had zero risk underbounds, and repeat source/consumer identities were exact.

## Execution and audit chain

The formal matrix completed:

- 12 fresh Blender 5.2 Cycles CPU renders;
- 6 multipart adapters;
- 6 Python and 6 Node consumers;
- 24 typed-envelope encoders;
- 1 analyzer;
- 56 unique successful child PIDs when paired with the corrected audit.

The first audit independently reproduced every payload, measurement and verdict but caught only 28/30 mutations. Both escapes altered `result.mutationAttacks[0].passed` and repaired `evidenceHash`; the validator had semantically checked the roster but omitted the roster array from its protected expected projection. The failure and missing original receipt remain preserved.

Audit-only C1 added the already checked roster and analyzer PID to that projection, bound every immutable parent and the original tool Git blob, and ran exactly one new Python audit process. It reproduced the bounded verdict and rejected 30/30 mutations without changing any measurement or rerunning Blender, adapters, consumers, envelopes or analyzer.

## Evidence identities

- preregistration commit: `22b0338aa2fcb168c4e94001bf9cbfe2d5a1e0f6`
- formal tool freeze: `006d3934b3cf625e9f7e85bd837f0f5889d2be45`
- audit-C1 tool freeze: `2dadbc3`
- result SHA-256: `1a569ace92b58b41b6faffe164778c5db35b1b0d7288ca3425f885ec5b0746a5`
- result evidence hash: `b459fe0e8048fd6cffc2a249ed0c4e0de431fd1e0f3beda0e339cca98718d55d`
- failed audit SHA-256: `2ecb05c5cb299e0b6c15dc9edb75e20a9edf5885e803883d7b310efaccf6ffac`
- corrected audit SHA-256: `fe77a26135d8021db6eb52f6e310392efd1a155f5712c99cd9dddbc1925708ee`
- corrected audit hash: `9064fca6a3dc060975e949d3018b737560e01fdeaeac780fb9a25e0729aa4170`
- correction receipt SHA-256: `12677054b85a325b803e6d59166d756306497c7b2e4159ae93bffe7f554f36a0`
- correction receipt hash: `0a7e20b39523f392b348b006450e62a8badb3192aab445b9a050593bab5d4217`

## Non-claims and next gate

D12.7 covers opaque, static, rigid, subpixel-residual Blender inputs only. It does not validate actual object/camera motion, deformation, disocclusion, transparency, hair, particles, volumes, noisy beauty renders, motion blur or human-perceived temporal quality.

The next defensible step is not to relabel this bounded result. A new preregistered holdout must make comparator quality explicitly report-only or explicitly mandatory before observing new fixtures, then test the adaptive rule on new rigid-motion and disocclusion scenes. Until that succeeds, the local-risk gate remains an evidence-backed static candidate rather than a production temporal policy.

Artifacts: `experiments/blender-static-adaptive-risk-gate-holdout-v0-1/`, `specs/blender-static-adaptive-risk-gate-holdout.v0.1.json`, and `specs/blender-static-adaptive-risk-gate-audit-c1.v0.1.json`.
