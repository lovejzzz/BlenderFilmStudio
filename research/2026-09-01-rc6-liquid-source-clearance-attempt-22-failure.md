# RC6 liquid source-clearance attempt-22 retained failure

## Verdict

`FAIL_EXECUTION / RETAINED_HARNESS_FAILURE`. The run stopped in the first cell before any fluid data bake, mesh bake, save or render. The independent failure audit passed 19/19 checks. The unique attempt-22 work and evidence roots must not be reused.

## Exact failure

- Tool-freeze commit: `8ee02894ca681618d1ad5f7301007cb726f76593`
- Spec hash: `c8eaf3df545c7cb3a5f2bbb35b59a6f202f49368f562b8d71dd7f57f7eaba381`
- Admission hash: `029b732e80ecbc13da836db6ceb03e220097e3262926f2784d4c67b69d371db4`
- Process hash: `54a74dcd798d87a6eb9ed5380a6afeaaff6f0a5398c68dfcdb695d3ecb295dd8`
- Failure hash: `41d141b491814ff676d504bb6e073e14f2499a8dc1ea0d5bbd7cc4759aee907d`
- One Blender start, 0.929 seconds, zero work bytes, zero renders, zero network calls and zero engine writes.
- Exact Blender error: `frozen source geometry identity mismatch`.

## Root cause

The inherited source-volume identity function transforms the source mesh into full world space before computing signed volume. Translation should not change volume mathematically, but floating-point cancellation changed the reported value when the source was moved before the identity check:

- Frozen pose `z=0.145`: `0.0013283283766940559 m³`
- Moved pose `z=0.150`: `0.0013283282353109553 m³`
- Translation-invariant linear transform at both poses: `0.0013283282518288175 m³`

The full-world difference of about `1.41e-10 m³` exceeded the frozen absolute identity tolerance of `1e-10 m³`. This is a measurement-order defect, not evidence against the clearance hypothesis.

## Versioned correction

Do not weaken the tolerance or mutate attempt-22. C1 must validate the frozen source volume and dimensions at the original retained pose first, then derive and apply the requested source-bottom clearance, assert the resulting placement, and continue with the unchanged four cells, physics settings, cache roster and scientific thresholds in a fresh attempt-23 root.
