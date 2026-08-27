# B52-D12.8 · Formal negative result and C2 audit-only protocol

Date: 2026-08-27

State: `FORMAL_MATRIX_COMPLETE · NEGATIVE_RESULT_IMMUTABLE · ORIGINAL_AUDIT_FAILED · C2_PREREGISTERED`

## Immutable formal result

The single formal D12.8-C1 matrix completed 72 producer/adapter/consumer/envelope processes, 16 real Blender 5.2 Cycles source renders, one independent analyzer and one independent audit: 74 unique process identities in total. The analyzer emitted `PROJECTIVE_MOTION_DISOCCLUSION_ADAPTIVE_GATE_NOT_SUPPORTED` with 9/14 checks and 40/40 registered mutations. The result file, raw payloads, execution record, failed audit and failure record are immutable.

This is a scientifically useful rejection. Transform-aware structural rejection passed, risk conservatism passed, all invalid/rejected pixels fell back to current float32 RGBA, the static control passed, the registered disocclusion/bounds/depth stresses were exposed, and the radius-3 comparator remained report-only. The unchanged static D12.7 risk rule did not generalize with usable coverage: the three moving primary fixtures retained only 16.98%, 0%, and 13.17% of radius-2 history. The camera-motion fixture therefore had an empty adaptive domain.

## Two independent limitations remain negative

Python and Node agreed byte-for-byte on all eight decision/reconstruction payloads in all eight cells. Their only raw divergence was `risk.rgb64`: 46, 88 and 16 float64 scalar differences per repeat in the three moving fixtures, with maxima of `2.168404344971009e-19`, `4.336808689942018e-19`, and `2.168404344971009e-19`. The static fixture was exact, repeat 1 equaled repeat 2, and the tiny arithmetic differences changed zero threshold-derived adaptive decisions. This is still a failed exact-identity contract, not permission to relabel it as passing.

`VECTOR_DEPTH_ORACLE` also remains false. Post-run inspection found that the frozen analyzer accumulated previous-depth relative error before excluding pixels whose correct structural reason was `INVALID_DEPTH`; the same-index depth-reveal stress therefore contributes a 0.289 maximum to a domain intended to describe valid history. C2 may record that measurement-domain defect, but it may not recompute the metric or change the check. A future fresh preregistration must separate valid-history depth agreement from expected disocclusion rejection.

## Original audit semantic defect

The original audit independently replayed every raw invariant, measurement, verdict mapping, comparator exclusion, mutation roster and process identity. It passed 9/10 checks. Its only false check, `DUAL_PAYLOAD_IDENTITY`, directly required all 72 Python/Node payload comparisons to be true. That requirement is appropriate as a scientific support gate, but not as the acceptance condition for an audit of a negative result whose analyzer already recorded those same raw differences as `SOURCE_ADAPTER_CONSUMER_IDENTITY=false` and `DUAL_AND_INDEPENDENT_REPLAY=false`.

The runner correctly retained `run.failure.json` and wrote no receipt. We do not overwrite that history.

## Sole permitted C2 action

C2 may add one new read-only Python audit process. It must bind the corrected D12.8 spec, accepted preflight, formal-root marker, execution, result, failed audit, failure record, original audit Git blob and its own frozen Git blob. It must recompute the complete float64 difference roster from immutable Python/Node bytes, verify the frozen per-cell counts/maxima/roster hashes and zero decision differences, require all non-risk payloads to remain exact, reproduce the exact five false and nine true result checks, validate the rejected verdict, retain the original audit's single false check, and account for the original 74 PIDs plus its own new PID.

It may write only `audit.c2.json`. It may not invoke Blender, any producer, adapter, consumer, envelope encoder or analyzer; change a byte of formal evidence; repair the depth metric; promote either identity check; change any threshold, measurement, verdict or non-claim; or invent an original-run receipt.

Machine-readable protocol: `specs/blender-projective-motion-disocclusion-adaptive-risk-audit-c2.v0.1.json`.
