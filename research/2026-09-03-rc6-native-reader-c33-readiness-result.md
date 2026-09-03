# C33 result — native cache reader ready

Date: 2026-09-03
Status: `PASS_READER_READINESS`, independent audit 28/28.

C33 built one small trusted diagnostic helper against the exact existing RC5
OpenVDB/TBB libraries; this was not an engine build. It passed known-value and
mutation controls for particle position, particle velocity, flag, dense
velocity and signed finite-grid phi. Its phi control counted active and
inactive negative tiles while excluding zero background. Missing attributes,
NaN, zero dimensions and inconsistent transforms all rejected.

Attempt-112 is retained as a pre-root manifest-order rejection. C1 attempt-113
passed all synthetic controls, copied and verified all108 C29 cache files, then
explicitly rejected the first real frame because Mantaflow's truncated point
codec was not registered. C2 added the same three type registrations used by
bound Mantaflow source and a matching independent fixture; it did not change a
physics parameter or weaken a check.

C2 attempt-114 passes. All36 copied real Data frames were decoded. A separate
Python/OpenVDB implementation independently reproduced every finite velocity
grid hash. The cache copy and both retained roots remained exact.

## Measured facts

- Result self hash: `a8c70df33c01b4aa39a61ad01dcc296744a69b714f5fba983e095cef0c4b0e55`.
- Audit self hash: `447d890263395a97f671782495ca2a045e905a14e696f62e0b0912d31f8fd1e0`.
- Helper hash: `4c6a84cce83768ab14734bd0b6bc0b6674baa0fa15097ea4de2a1f4f2c32b9d6`.
- Real grid roster on every frame: `particles`, `velocity`; no `phi`.
- Particle attributes: index-space `P`, stored `particles_velocity`, flag `U`;
  actual codecs are truncated `vec3s` and `int32`. VDB half storage is active.
- Every particle and velocity semantic hash is distinct across 36 frames.
- Decoded particle roster falls from13,659 at frame1 to3,820 at frame36,
  a 72.0331% reduction. Because Mantaflow can resample particles and because
  these old files lack phi, this is a strong loss signal but not exact mass.
- Runner 12.666 seconds; peak child RSS 911,704,064 bytes; workspace16,853,781
  bytes and evidence237,362 bytes. All are below frozen limits.
- Zero Blender starts, bakes, renders, engine builds/edits and gate network.

## Decision

Reader readiness is closed. C34 may be designed as one fresh uninterrupted
Data-only exact-C29/R40 bake that changes cache export to resumable, with no
Mesh or render. It must use this exact reader to measure native `phi` and use
common particle/velocity decoded hashes to test whether observation was
passive. A common-field mismatch is retained as failure/inconclusive; native
phi volume cannot clear the existing physical FAIL by itself. Freeze actual
roots, host/resources, execution lifecycle, field roster, comparison and
negative controls before the bake.

This result establishes a reader and a previously hidden loss signal. It does
not observe real-impact phi, prove cache passivity, identify one solver
operation, repair the liquid or improve film lighting.
