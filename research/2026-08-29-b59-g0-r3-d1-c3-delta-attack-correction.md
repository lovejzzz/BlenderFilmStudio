# B59-G0-R3-D1-C3 · Aggregate-claim attack correction

Date: 2026-08-29
Status: IMPLEMENTED AND REHEARSAL-VALIDATED
Formal D1 root: absent

The C2 rehearsal passed 7/7 observed gates, but only 8/10 attacks. A06 and A07 mutated reported Colima/host deltas, then the generic bundle resealer recomputed the aggregate and erased each mutation. The retained result and audit hashes are `5967c303fbebc06a714e7d69944e9d3f4351fee24f516a6963451751a807d3c3` and `5689f63ae5e1106a1789084b15df42df5527c6420cdf2d1f30e27d6b781fbd16`.

C3 gives aggregate-claim attacks a result-only reseal: samples stay unchanged, the forged aggregate is self-hashed, and independent recomputation must reject it. All observed parsing, thresholds and decisions remain unchanged. The failed rehearsal is retained under `experiments/codex-host-disk-attribution-c2-rehearsal-v0-1`.
