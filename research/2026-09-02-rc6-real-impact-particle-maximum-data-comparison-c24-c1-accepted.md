# RC6 C24 C1 — accepted particle-maximum Data/Mesh comparison

C24 closes by corrected attempt-103 as `PASS_DIAGNOSTIC` with classification
`MIXED_ONSET_AMPLITUDE_RESPONSE`. The producer checks pass 8/8 and the
independent audit passes 24/24.

Exact identities:

- execution commit: `cd95711af948422c054f398523247e5c2f4f3e9a`
- result self hash: `ed8d1d6cc7d039b6d85fc3a9cff73379943648311070e0eb93a77c4421768736`
- receipt self hash: `71c6639bbf8b82c4eb7b68d9fb752061d34b41b8a2886076583bf240d63df961`
- audit self hash: `505c4d79491c28a524bde3b8eb5c2eb1588fee783dd4a88ded25b1893aeea7d4`

## Recomputed comparison

| Signal | C18 max16 | C23 max12 | Interpretation |
| --- | ---: | ---: | --- |
| velocity-support `+25%` onset | frame 24 | frame 24 | unchanged |
| particle-support `+25%` onset | frame 25 | frame 25 | unchanged |
| Mesh-volume `+25%` onset | frame 24 | frame 25 | delayed one frame |
| maximum velocity expansion | 173.840445% | 122.542386% | improved |
| maximum particle expansion | 32.384342% | 55.144586% | worse |
| maximum Mesh expansion | 51.543955% | 69.314260% | worse |

Current particle/Mesh and velocity/Mesh curves remain strongly correlated at
`r=0.98667` and `r=0.98632`, respectively. Occupied support is not exact liquid
mass and the mixed response does not identify one internal operation.

The complete physical C23 result remains the decision authority: source error,
temporal drift, fragmentation timing and cup intrusion all regressed. Therefore
the smaller maximum is rejected despite lower peak velocity support and one-
frame-later Mesh threshold crossing.

Attempt-102 remains immutable as the one-token harness failure. Attempt-103
used two engine-Python starts, copied the cache into a fresh root and made zero
Blender starts, bakes, renders, saves, network calls or retained-root writes.

Close the `particle_maximum`/`particle_minimum` scalar family. The next gate is
one read-only C25 bound-source inspection to select exactly one distinct Data-
layer degree of freedom. No new bake or render may precede that selection.
