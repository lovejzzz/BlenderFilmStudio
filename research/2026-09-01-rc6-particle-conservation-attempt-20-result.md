# RC6 particle-conservation matrix attempt-20

Date: 2026-09-01  
Execution: `PASS_EXECUTION`  
Scientific verdict: `FAIL_STATIC_CONTROL`  
Independent audit: `PASS 22/22`

## Corrected semantics

Development component diagnostics proved that the two recurring closed surfaces
were concentric and oppositely oriented. At one representative frame the outer
surface was about `+0.002043 m³` and the inner surface about `−0.000956 m³`;
their signed difference matched the aggregate liquid volume. Connected-component
count alone had therefore conflated a nested reconstruction shell with disjoint
water fragments.

Inspection of the bound Blender source at commit
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6` also showed that `volume_density`
is evaluated only for gas flows. A controlled liquid run changing only that
property produced identical results. The frozen attempt consequently restored
the liquid source `surface_distance=0.0`, retained signed component diagnostics,
fixed `mesh_particle_radius=3.0`, and varied only simulation `particle_radius`.

## Results

| simulation radius | max source-volume error | max temporal drift | max components | max outside cup + 1 voxel |
| --- | ---: | ---: | ---: | ---: |
| 1.0 | 40.73% | 27.94% | 2 | 0.00% |
| 1.3 | 32.89% | 13.76% | 2 | 0.00% |
| 1.6 | 31.28% | 6.50% | 6 | 2.98% |
| 2.0 | 37.15% | 8.00% | 2 | 0.00% |

The official parameter direction was confirmed: increasing simulation particle
radius substantially reduced temporal leakage, with a local optimum near 1.6
in this screen. It did not correct absolute reconstructed volume, and radius 1.6
also introduced small additional components and bounded cup-overlap failures.

## Decision

Do not unlock slow-tip. Fix simulation radius at 1.6 for the next reconstruction
screen and vary only `mesh_particle_radius`. That parameter is responsible for
visible mesh-particle size and can test whether a larger surface kernel both
matches the frozen source volume and merges the small components. The acceptance
thresholds remain five percent for source-relative and temporal error, one
positive water body with at most one nested negative shell, one-voxel cup
containment, closed manifolds and zero renders.

## Bound evidence

- Matrix hash: `0d01a6c36ac3714da67c128813ea612e2d76a59be3c49cd3f2de9ffe89e991bc`
- Independent audit hash: `fbcc5f297ef111c40cd0e8b4715c3d40a8da79433b44e7634753e73ed8e8cf4e`
- Evidence root: `experiments/physical-richness/RC6-2026-09-01-particle-conservation-attempt-20`
- Work root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-particle-conservation-attempt-20`
