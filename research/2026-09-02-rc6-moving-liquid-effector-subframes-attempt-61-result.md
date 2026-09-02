# RC6 moving-liquid effector-subframes attempt-61 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-61 retained the exact attempt-59 2.0-cell physical configuration and
changed only moving-cup effector subframes from 1 to 2. The additional temporal
obstacle sample did not repair conservation.

Maximum temporal Mesh loss worsened from 23.03% to 23.84%, and maximum source-
relative error worsened from 24.00% to 24.80%. The latter still passed the
unchanged 25% source gate, but temporal conservation again failed the unchanged
15% ceiling. Every other physical check passed: exact C5F96 solver motion, one
positive manifold liquid body, zero radial/floor/rim escape, 36.03 mm cup-local
liquid motion and the exact 72-file cache roster.

Data time increased from 251.55 to 288.35 seconds (`+14.63%`); Mesh took 2.90
seconds. The process counts remained one Blender, one Bullet, one Data and one
Mesh bake with zero render, save, network or engine write. The result, receipt
and audit self hashes are
`20de67bb304d99f7194d5c5766f20387beddfc29fddaf9b6eb71112cae82a83a`,
`57e3ade83e3357dff8c97c56d4aaa31660b46eb7c8d8a15023f8034182275c80`
and `ebf3945235336500fc70fec10066e9045d607bdf4d73b1e62820aa0ab358bada`.

No third subframe value is allowed. Before selecting solver minimum timesteps
as the next different physical degree of freedom, one zero-Blender copied-cache
diagnostic should compare attempt-61 Data occupied-voxel support with the
attempt-59 one-subframe baseline.
