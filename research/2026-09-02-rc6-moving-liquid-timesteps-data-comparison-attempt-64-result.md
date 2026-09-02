# RC6 moving-liquid timesteps Data comparison attempt-64 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`; independent audit `19/19 PASS`

Attempt-64 copied the complete immutable attempt-63 cache and compared all 24
particle occupied-voxel supports with the one-timestep attempt-60/59 baseline.
It performed zero Blender starts, bakes, renders, saves, network calls or
retained-root writes.

With `timesteps_min=2`, occupied Data support fell from 1,330 to 983
(`-26.09%`). The one-timestep baseline fell `-26.67%`, so the final-frame Data
improvement was only 0.58 percentage points; the worst-frame loss improved only
from 27.42% to 26.99%. The retained Mesh curve improved 1.33 points, and the
current Data/Mesh curves remain strongly correlated (`r=0.97958`), but the
per-frame changes do not move together (`r=-0.21839`). The frozen
classification remains `DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS`.

Result, receipt and independent-audit self hashes are
`dcaa7470889c74e7e389c1fd74a145395d40897630fb95f7357c8a1069fe60d0`,
`72e83b26c74aeff93aecb27e4b85d590520248452d92945735d41fe822fb9e6b`
and `4fa13dbb622c3dce692e555a87589fa96e0431f0bb74a64dd460d6b615a75533`.

Minimum-timestep tuning is closed: no value 3, CFL change or maximum-timestep
change is allowed. The two-step result is a modestly better current baseline,
not a moving-liquid pass. The next experiment may change exactly one different
simulation property, particle radius, while preserving the exact trajectory,
surface distance, one effector subframe, Mesh settings and scientific gates.
