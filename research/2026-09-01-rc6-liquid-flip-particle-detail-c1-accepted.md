# RC6 FLIP particle detail C1 accepted

Status: **PASS (11/11)**

The audit-only C1 correction passed without starting Blender, rebaking fluid, saving a scene, rendering, or changing retained attempt-37. It corrected only the numeric provenance rule for values derived from separately rounded eight-decimal coordinates: after the source value and the coordinate are each rounded once, independent recomputation may differ by one unit in the last reported decimal (0.00000001 m).

All categorical and exact-identity requirements remained unchanged:

- every outlier detail self hash passed;
- ALIVE state, per-axis classification and modeled-cup physical region passed;
- the prior 26 successful attempt-37 checks remained bound;
- the earlier aggregate particle result remained byte-exact;
- the exact Blender source implementation remained bound;
- retained attempt-37 remained immutable.

## Accepted finding

The static resolution-192 control contains nine unique active FLIP particle positions embedded in the modeled cup's solid floor. They appear on frames 4–7, report zero RNA speed, and remain at identical coordinates across those frames. Their interior-floor penetration is 13.96487-20.23688 mm; all remain above the cup's -0.22 m outer bottom. This is a small persistent embedded particle cluster, not an active through-cup leak.

The next physical gate must therefore test cluster formation during the solve, beginning with bounded Preview/Review timestep/CFL and collision settings. Surface concavity is not the repair: the same nine particles were amplified into 7,814 below-floor mesh vertices, and earlier surface-only changes traded the visible defect for missing volume and fragmentation.

## Binding

- C1 audit hash: `840b8b91e9af9b9c36775297314900214c4c9313c34947294e2d48f358b160cf`
- C1 audit file SHA-256: `5e16d4701c9e3d3721ae580e019757ad60fa3650b09cc68546f17e9c0abe3b1b`
- C1 root-manifest hash: `22f1ef6d6d45728d56418731117f789003326d64539cbe64081cf2b461062a4d`
- C1 root-manifest file SHA-256: `6971b370fd2df55c73d6dff25bce5d49b42e468d96e281ba41cf9282ae303738`
- Retained result hash: `e3e52359bfc4d2191b162384b9b5890e547416defc1ead4c0fdd025f708f3794`
- Retained execution receipt hash: `5c32c481138382fef4864ec539436f8c090bfdf2f2a4f5675fd25054ffac11b2`
- Retained failed audit hash: `7667372e092c968930ac5a32385e72a335ec13682c1df3a2299a97bceb7fcf60`

Claim ceiling: this validates localization and state of the already measured cached outliers only. It does not yet prove why the cluster formed, a corrected collision solve, slow tipping, a finished impact, or final rendered-film quality.
