# RC6 moving-liquid fractional-obstacle distance attempt-68 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-68 returned to exact attempt-65 physics and changed only positive
fractional-obstacle distance from the bound default 0.5 to 0.25. Particle
minimum/maximum remained 8/16, simulation radius remained 1.8, and all motion,
Mesh and acceptance fields stayed frozen.

The reduced separation produced another material improvement without obstacle
intrusion. Maximum temporal Mesh loss fell from 17.05% to 15.44% (1.61
percentage points), and maximum source-relative error fell from 22.10% to
18.81% (3.29 points). Radial, below-floor and above-rim fractions remained zero
on all 24 frames; the liquid stayed one positive manifold body. The unchanged
15% temporal ceiling still failed by 0.44 percentage points, so 16 of 17
physical checks passed.

Data and Mesh took 287.09 and 2.92 seconds, an 8.13% Data-cost increase versus
attempt-65. Result, receipt and independent-audit self hashes are
`f12dd9168e0bc646c84ea5ea4faaa9b50c718db051a27686660261cfcf8a3dc1`,
`6037c9cc557ca228fcbc8b60c20c4cad25ffb84f4c5cadbd6f40c47957d01f84`
and `8716e9601f8d8576cc062e2502c90f4b0a1ac1e30c05b9c626a3abf1e13d6115`.

Fractional-distance tuning is closed. Before choosing another different
simulation property, compare this immutable Data cache with attempt-65/66 to
determine whether the near-pass improvement begins before Mesh reconstruction.
