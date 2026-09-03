# RC6 C35 result — operation order selects resolution convergence

Date: 2026-09-03
Verdict: `PASS_SOURCE_ORDER_SELECT_REVIEW128_DATA_ONLY`, 22/22.

C35 binds the accepted C34 curves to exact RC5 Mantaflow source without
starting Blender or changing a cache. It also closes the C34 narrative onset
context: current phi first reaches `-15%` relative to frame 1 at frame 31,
while C29 Mesh reaches the same frame-1-relative line at frame 25. C30's Mesh
frame 31 was relative to a different coherent frame-22 baseline. Transition
ordering remains inconclusive; the strong final loss/correlation still rejects
a purely Mesh-only explanation.

## Bound operation order

Within a liquid substep the source performs particle advection, obstacle push,
the beginning-of-adaptive-frame previous-phi copy, current-phi advection,
particle-levelset construction, current-phi shrink/join, pressure, particle
resampling and finally APIC grid-to-particle update. Therefore:

- current phi and particle phi are both formed before the same substep's
  `adjustNumber` call;
- saved particles are post-resampling, so particle cardinality is not a
  same-stage mass measurement;
- resampling can affect the next substep and cannot be excluded as a temporal
  contributor;
- `flip_ratio` is used only by the non-APIC branch and is not a C29 control;
- native level-set width, grid/velocity combination width and particle radius
  support are expressed in cell units, so their world-space scale changes with
  resolution.

## Selected next gate

C36 may test exactly one numerical change: `resolution_max 96→128`, the already
frozen REVIEW tier, on otherwise exact C34/R40 settings. It remains
uninterrupted, resumable, Data-only, with no Mesh or render. The question is
whether normalized native-phi loss converges as cell-scaled numerical support
shrinks in world units. This is not a physical parameter recipe and does not
admit the 36-frame request through the current product PREVIEW API.

## Evidence

- Freeze/execution commit: `887f7bde`.
- Evidence:
  `experiments/physical-richness/RC6-2026-09-03-native-phi-operation-order-c35-attempt-117`.
- Observation self hash:
  `08c1ae2b10d3aaeef083e0d55469bb3a790bb9f68bb3c560ba7c1dab804090e4`.
- Audit self hash:
  `419d176f190d34b52dcd16c8a073040ab42c4e8e694498d19ff6e05d1c0a87bf`.
- Counts: one system-Python audit; zero Blender, bake, render, cache copy,
  retained write, build, engine edit or network operation.

C29 remains physical FAIL25/27. C35 does not establish exact mass, same-frame
causality, a responsible solver operation, repaired physics, Mesh equivalence,
visual quality or permission to tune lighting.

