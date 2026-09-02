# RC6 real-impact liquid C16 result

Date: 2026-09-02

## Verdict

`FAIL_REAL_IMPACT_LIQUID_CFL_C16`, with an independent `20/20 PASS` audit.
The failure is a retained physical result, not a harness failure.

## Exact intervention

C16 changed only Mantaflow `cfl_condition` from `2.0` to `1.0` on the C14
baseline. Minimum/maximum timesteps remained `2/8`; the R40 Bullet trajectory,
Preview-96 domain, source, obstacle, particle, Mesh and all 27 acceptance checks
remained frozen.

## Result

- Physical checks: `22/27`; the five failures are source-volume conservation,
  temporal drift, positive-body count, connected-component count and largest-
  component dominance.
- Peak reconstructed volume is `15.11373886×` source, compared with C14's
  `3.35700078×`.
- Maximum positive bodies are `219`, compared with C14's `50`; maximum connected
  components are `221`, compared with C14's `52`.
- The first source/temporal failure moves forward to frame 24, and the largest-
  component failure begins at frame 26. C14 stayed within those gates until
  frame 35 or later.
- Maximum cup-solid intrusion improves from C14's `2.453988%` to `0.689783%`,
  so the unchanged one-percent intrusion gate passes.
- The exact retained R40 Bullet path remains unchanged before and after fluid;
  all domain, ramp, floor, manifold, provenance and zero-outcome-pose checks pass.
- Data/Mesh cost is `1652.8074 / 5.8544 s`; total product-process wall time is
  `1674.6957 s`. There were zero renders, saves, builds, network calls, engine
  source edits or engine remote writes.

## Interpretation and next gate

Lower CFL is not monotonic stability control in this moving-obstacle APIC case.
It trades cleaner obstacle separation for much earlier, much larger liquid
expansion and fragmentation. More adaptive solver updates can also mean more
particle adjustment and obstacle interaction; this result does not prove which
per-step operation causes the divergence.

CFL tuning is closed after the one frozen value. The next gate is one fresh,
zero-Blender copied-cache C17 comparison between immutable C16 and C14 Data/Mesh
curves. It must locate particle/velocity-support onset before selecting another
distinct physical variable. Do not run a second CFL, increase maximum timesteps,
tune Mesh, render or weaken any gate.

## Evidence

- Evidence root: `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88`
- Workspace root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-cfl-c16-attempt-88`
- Execution commit: `2e31ccde1e2e21ef94bbf970c8438801767aeccf`
- Result self hash: `4a331e01fc633b88106f79fcd32be99cb9997bfbc88e2cddeec960b858882372`
- Receipt self hash: `5fe859639684644c1b2bd78ce6caddb5ec0136e1cec3d56c7fcec0ecf6cf3dab`
- Independent-audit self hash: `ecbb4639f7e4dd5bf4bc0a0fa936df48d5299befaa038b3c332d192b52a7ebb6`
- Work manifest self hash: `b6fd9430397d3951ab84d2a0264fbec65f47217ba6711dc063fa4374f25f1e1b`
- Final evidence manifest self hash: `100e8389ac0cd002ef8764cc888d8f02ef81d0c0ba03d1dee3bb711ea8476e57`
