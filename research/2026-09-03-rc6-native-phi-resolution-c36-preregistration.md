# RC6 C36 preregistration — Review128 Data-only convergence

Date: 2026-09-03

C36 changes exactly one numerical setting from accepted C34:
`resolution_max 96→128`. The 0.9 m maximum domain dimension therefore changes
the derived base voxel from `0.009375 m` to `0.00703125 m`. Every R40 physical
input, APIC setting, particle/boundary value, frame 1–36 lifecycle and
resumable native export remains unchanged.

The run is one uninterrupted Data bake with no Mesh, render, scene save,
pause/resume, physical scalar, engine edit/build/write or network operation.
It must retain exact R40 rigid motion, all 36 actual native-field rosters and a
fresh bounded cache. The accepted C33 reader and exact bundled OpenVDB Python
independently decode all scalar fields and full velocity grids.

Current phi and particle phi are normalized separately to their own frame-1
occupancy. Review128 supports numerical resolution convergence only if both
absolute frame-36 losses improve over C34 by at least 5 percentage points and
neither first 15% loss crossing moves earlier. If both improve but miss that
gate, classify `DIRECTIONAL_BUT_BELOW_CONVERGENCE_GATE`; otherwise classify
`NO_CONVERGENCE_OR_REGRESSION`. Every classification is retained and none is a
physical PASS, exact-mass claim or product recipe.

Workspace is capped at 8 GiB, evidence at 128 MiB, free-space reserve at 100
GiB and the single Blender start at two hours. The existing binary is used;
the separate 160 GiB clean-build threshold remains unmet. No Mesh or lighting
work is allowed by C36.
