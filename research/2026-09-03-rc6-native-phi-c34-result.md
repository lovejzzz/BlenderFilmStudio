# RC6 C34 result — native level-set loss is observable before Mesh

Date: 2026-09-03
Accepted verdict: `PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE`.

C34 repeated the exact retained C29 R40/Preview-96/APIC Data simulation with
one observation-only setting: uninterrupted resumable Data export. It generated
no Mesh and no render. Across all 36 frames, the decoded particle position,
particle velocity, particle flag and full dense velocity grid are exact against
C29, including type, dimensions, voxel size and storage precision. This makes
the added native fields usable for this exact same-host uninterrupted Data
path; it does not prove equivalence for pause/resume or Mesh loading.

The native current `phi` negative-levelset occupancy falls from
`0.0022692263 m³` at frame 1 to `0.0016520693 m³` at frame 36, a `-27.1968%`
change. `phi_particles` falls `-30.3195%`. Current `phi` first crosses a 15%
loss relative to its own frame 1 at frame 31—the same frame at which retained
C29 Mesh first crossed its loss line—and its 36-frame correlation with C29
Mesh volume is `r=0.89898`. These are descriptive cross-checks, not new frozen
acceptance thresholds.

This materially narrows the diagnosis: C29's visible loss is not only a Mesh
reconstruction artifact. A native Data-level-set representation also loses
finite-grid support while the exact same particles and velocity are observed.
It still does not identify one solver operation or measure exact mass. Native
phi is reconstructed numerical occupancy; `phi_particles` is sampled at a
different solver stage, and `phi_previous` is a prior-state field that must not
be interpreted as current volume.

## Evidence and retained failure

- Freeze commit: `44a82b2407833a07a204b13cee404449fd9fa2e9`.
- Attempt-115 workspace:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-03-native-phi-c34-attempt-115`.
- Attempt-115 scene checks: 14/14; 36 Data frames; 72 exact cache files;
  Data bake `1065.2735 s`; zero Mesh/render/save/build/network/engine writes.
- Diagnostic result hash:
  `9c5a63ab8d54114108c8c553d511b74b3f8f2e1722ec6461d92de9a005a34a2f`.
- Attempt-115 remains an immutable harness `FAIL_RETAINED`: its audit selected
  Homebrew Python, where `openvdb` is unavailable. It failed during import,
  before reading a cache or writing an audit.
- C1 attempt-116 changed only the audit interpreter to the exact RC5 bundled
  Python 3.13 and read attempt-115 without copying or modifying cache data.
- C1 independent audit: 22/22, self hash
  `d8d61cbe01b1caec51742e70a9cce8d2003dbe22151835a3ea716575398f0db2`.
- C1 receipt self hash:
  `b90f6345bde951798642c8e37225a35341d0fb03b3f347abc202cf9de64bc15e`.
- C1 operations: one audit Python start; zero Blender, bake, render, cache copy,
  retained write, build, engine edit or network operation.

## Decision and next step

C29 remains physical FAIL25/27 and is still forbidden from visual promotion.
Close native-export passivity for this exact path, but do not call the liquid
conservative or repaired. C35 must be a read-only bound-source operation-order
inspection: bind the meanings and update order of current phi, particle phi,
particle resampling and obstacle handling, then either preregister exactly one
distinct Data-layer physical intervention or stop if the source/evidence is
insufficient. No new bake, Mesh, render, band-width scan or exact-mass claim may
precede that inspection.

The owner's visual feedback is retained for the later accepted-physics stage:
realism is promising, but lighting needs stronger hierarchy. That stage will
compare fresh screenshots for directional key, controlled fill, background
separation, contact shadow and collision-beat emphasis rather than randomly
adding lamp power.
