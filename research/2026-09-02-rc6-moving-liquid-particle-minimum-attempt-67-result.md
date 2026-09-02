# RC6 moving-liquid minimum particles-per-cell attempt-67 result

Date: 2026-09-02

Verdict: retained physical `FAIL`; independent audit `16/16 PASS`

Attempt-67 preserved exact attempt-65 physics and changed only continuing
`particle_min` from the bound default 8 to the preregistered midpoint 12.
`particle_max` remained 16 and initial `particle_number` remained 2.

The change did not alter the physical result. Maximum temporal Mesh loss stayed
exactly 17.050045%, source-relative error stayed exactly 22.099910%, and every
topology, containment, motion and centroid metric was identical. All 24 Mesh
cache files were byte-identical to attempt-65; all 24 Data VDB files changed,
showing that internal particle data changed without affecting reconstructed
geometry. Data time increased from 265.50 to 278.27 seconds (`+4.81%`).

The unchanged 15% temporal gate therefore remained the sole failure, with 16
of 17 physical checks passing. Result, receipt and independent-audit self hashes
are `92508f4aef527b546f0417860e5d9f412fb7d36cd616739c662acd7cff4eb577`,
`22e0ad0c8b60b5ab3267d6a09b6fc6989f913766149eec61ebe40b1acc0b2d7b`
and `6a35f1ac03cc927b72e41b97bc350d28afc398443c7a4090983e822c56447f97`.

Particle-density tuning is closed. The next source-led design should target the
moving fractional-obstacle boundary, where bound `fractions_distance` controls
how far particles are pushed from the obstacle, while preserving the exact
attempt-65 particle-radius and all Mesh and acceptance fields.
