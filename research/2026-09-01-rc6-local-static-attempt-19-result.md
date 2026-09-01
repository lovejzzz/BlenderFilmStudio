# RC6 local-domain static control attempt-19

Date: 2026-09-01  
Execution: `PASS_EXECUTION`  
Scientific verdict: `FAIL_STATIC_CONTROL`  
Independent audit: `PASS 24/24`

## What improved

The cup-local domain was reduced from `2.5 × 1.6 × 0.9 m` to
`0.36 × 0.36 × 0.50 m` while preserving a `5.2083 mm` base voxel at
resolution 96. Each seven-frame data/mesh solve plus baked-state save completed
in about `103–115 s`. All four cells completed in one bounded run with zero
renders, zero network calls and zero engine writes. This replaces the old
three-hour discovery loop with an approximately eight-minute four-candidate
screen.

## Why it still failed

No `mesh_particle_radius` candidate passed the frozen static thresholds:

| radius | max source-volume error | max temporal drift | max components | min largest component | max outside cup + 1 voxel |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 46.23% | 37.02% | 2 | 59.83% | 0.00% |
| 1.1 | 26.23% | 12.12% | 23 | 47.42% | 59.72% |
| 1.2 | 32.95% | 18.08% | 2 | 59.18% | 0.00% |
| 1.3 | 34.84% | 17.56% | 2 | 59.49% | 0.00% |

Radius 1.1 is only the relative source-volume winner. Its 23 components and
large outside-cup fraction make it especially unsuitable as water. It is not
an accepted candidate and does not unlock slow-tip.

## Product lesson

Localizing the domain fixed iteration cost and improved spatial coverage, but
did not fix particle-to-surface conservation or connectedness. Domain size and
surface reconstruction must therefore be independent admission dimensions in
the product, not one combined quality preset.

The next correction is diagnostic rather than another parameter sweep: rebake
one representative two-component cell in a fresh root, measure per-component
volume, area, centroid, bounds and cup containment in the same process, and
save a relative-cache baked state. This will distinguish a substantial second
water body from a thin reconstruction shell or collision-boundary artifact.
No slow-tip, impact or lighting run is authorized by this result.

## Bound evidence

- Matrix hash: `05170c406ca4b1dc3e035096f899ba72e9b015908ffed5f6b498404cfd608cb9`
- Independent audit hash: `4751b2b42a8b70758e225b8a457473c1d256cb8bde1ee4f436d198da0b2bcc8a`
- Evidence root: `experiments/physical-richness/RC6-2026-09-01-local-static-attempt-19`
- Work root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-local-static-attempt-19`
