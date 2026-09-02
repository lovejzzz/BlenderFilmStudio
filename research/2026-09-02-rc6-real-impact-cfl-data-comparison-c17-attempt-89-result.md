# RC6 real-impact C17 CFL Data comparison result

Date: 2026-09-02

## Verdict

`PASS_DIAGNOSTIC`, classification
`DATA_MESH_EXPANSION_WITHOUT_PRIOR_CUP_INTRUSION`, with an independent
`22/22 PASS` audit.

## Measurement

C17 copied all 108 immutable C16 cache files into a fresh root and read only
the copy. It made zero Blender starts, bakes, renders, saves, network calls or
retained-root writes.

Against coherent frame 22, C16 crosses the same frozen 25% expansion line in
both Data particle support and Mesh at frame 24:

- particle occupied support: `1447 → 1820`, or `+25.7775%`;
- velocity occupied support: `10958 → 30862`, or `+181.6390%`;
- Mesh volume: `0.0013587037 → 0.0019578935 m³`, or `+44.1001%`.

Positive-body, source-volume and temporal-volume checks also fail at frame 24;
connected components fail at frame 25. No frame in the comparison window
crosses the one-percent cup-solid-intrusion threshold. Particle support and
Mesh correlate at `0.99749857`; velocity support and Mesh correlate at
`0.93084124`. C14 did not cross the particle/Mesh comparison lines until
frames 36/35.

## Interpretation

The CFL regression begins in Data at the same measured frame as Mesh expansion
and without prior excessive cup intrusion. This rejects a Mesh-only repair and
rejects cup-solid intrusion as the necessary leading cause of C16's early
failure. Occupied support is still not exact mass, and the result does not prove
which per-step operation creates the instability.

CFL tuning is closed. The next physical test returns to the materially better
C14 CFL=2 baseline. Bound source routes `fractions_threshold` directly into
`updateFractions`; its RNA contract says higher values tag boundary cells as
obstacles more readily and reduce boundary smoothing. C18 may test only the
first UI-step value `0.05 → 0.10`, with every other C14 field and all 27 gates
frozen. It must be preregistered before any bake.

## Evidence

- Evidence root: `experiments/physical-richness/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89`
- Workspace root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-cfl-data-comparison-c17-attempt-89`
- Execution commit: `d6d032cf1dc13c36592c9925cb768b08531a3556`
- Result self hash: `dbbeb5ffbf3ab503fbac361b3d6d33467f83abd6de8f68e9c462b1998065f38d`
- Receipt self hash: `7be7b5bac36bb1c8aa90c1e431e91191ee081af068310be47ed0bbf1afd98e1f`
- Independent-audit self hash: `1884fa34ba995ee880015c51e1562d179ab104d2b5045a58d16c70df75fca80c`
- Work manifest self hash: `ce2113064d042805a4ffcca6b4a7330ad45b8f7a8cf4e256708b0ae0f3f129d1`
- Final evidence manifest self hash: `eecfcfba7858b2041f4be52ed60c11ba35a504dcd7334235fee0808069cbcfb6`
