# RC6 moving-liquid subframes Data comparison attempt-62 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`; independent audit `19/19 PASS`

Attempt-62 used the reusable copied-VDB comparison tool to bind subframes-2 as
the current run and subframes-1 as the baseline. It copied the complete
immutable attempt-61 cache and performed zero Blender, bake, render, save,
network or retained-root write operations.

With two subframes, occupied Data support fell from 1,335 to 970 (`-27.34%`),
which is 0.67 percentage points worse than the one-subframe baseline. The bound
Mesh curve was likewise 0.81 points worse. Current Data support and Mesh volume
remain strongly correlated (`r=0.96060`). The frozen classification is
`DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS`.

Result, receipt and audit self hashes are
`3a0ab8a413d15247220fca5e05bb81791740295d9cd146cfd64ad63d21c27c4e`,
`97663618e1c041ebb22408f58b71a509e3e50c84acc1b05f24bdef8b95501efe`
and `a847bffe1392a9a735a6281e6df6a17d49bc250d08060f3653db3261da04be9f`.

Effector-subframe tuning is closed; no value 3 is allowed. The next physical
gate may return to the better 2.0-cell/subframes-1 attempt-59 baseline and
change exactly one solver variable: minimum fluid timesteps per frame from 1
to 2. Mesh, motion and all acceptance thresholds remain unchanged.
