# RC6 moving-liquid fractions-distance Data comparison attempt-69 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`; independent audit `19/19 PASS`

Attempt-69 copied the exact immutable attempt-68 cache and compared all 24
occupied-voxel supports with attempt-66's analysis of the fractions-distance
0.5 attempt-65 cache. It performed zero Blender, bake, render, save, network or
retained-root write operations.

At fractional distance 0.25, occupied Data support fell from 1,230 to 940
(`-23.58%`) versus `-28.91%` at distance 0.5, a 5.33-point improvement. Mesh
temporal loss improved 1.61 points to 15.44%. Current occupancy and Mesh curves
correlate at `r=0.92964`, and their changes versus baseline correlate strongly
at `r=0.86588`. The classification remains
`DATA_SPATIAL_SUPPORT_SHRINK_PERSISTS`, but the near-pass improvement is clearly
present before Mesh reconstruction.

Result, receipt and independent-audit self hashes are
`7157d77aaddcef360bbe8bcfc4b418845c83fd99086545374d2a3fb11e876f87`,
`09483a370961959364ed168600c9083b14d9a0097b3339f0bb66c7a6cb72124c`
and `0da61c54796474f02af3329ee8b9284f04e8b4f140f7ffd6a33736154b09a692`.

Fractional-distance tuning remains closed. The next distinct Data-layer
property may increase `particle_band_width` from its bound default 3 to 4 on
the exact attempt-68 baseline, because the source passes this width to every
`adjustNumber` call and documents that a thicker band carries more particles.
