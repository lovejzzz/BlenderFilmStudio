# RC6 moving-liquid effector-distance Data occupancy attempt-60 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`; independent audit `19/19 PASS`

Attempt-60 copied the complete immutable attempt-59 cache and read all 24
particle/velocity VDB metadata records with the exact product Python and
OpenVDB runtime. It started Blender zero times and performed zero bake, render,
save, network or retained-root write operations.

At the 2.0-cell effector distance, particle occupied-voxel support fell from
1,335 to 979 (`-26.67%`). That is only a 2.10-percentage-point improvement over
the 2.5-cell attempt-58 baseline, while the bound Mesh curve improved by 11.20
points. The current Data-support and Mesh-volume curves remain strongly
correlated (`r=0.95525`). Data support crossed the unchanged 15% loss boundary
at frame 12, when the cup tilt was only 6.84 degrees; Mesh crossed it at frame
16, near 9.36 degrees.

The frozen classification is
`DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS_AT_2P0`. Occupied sparse voxels are not
exact mass, but the remaining moving-liquid failure exists before surface
reconstruction and cannot be repaired honestly by Mesh tuning.

Result, receipt and audit self hashes are
`6af44108a6cc4d00d10de62a808c7b612ec1f1c3335a988e2fc01da3138605c5`,
`fcae7479a9e749c2395e3f8015f9de205174d1671fa97a586bef693b8f2db907`
and `b4b5558428cdc17dd5a2d5bf2917e53107ffb03c5ea1d7b10dd3338c241cef30`.

The next physical gate may change exactly one different degree of freedom:
moving-effector subframes from 1 to 2. It must keep the accepted C5F96
trajectory, 2.0-cell effector distance, all simulation/surface settings and all
scientific thresholds unchanged. No second effector-distance value, Mesh tune,
impact or render is allowed.
