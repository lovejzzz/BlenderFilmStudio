# RC6 real-impact Bullet speed screen preregistration

Date: 2026-09-02

## Physical question

Which of three frozen striker speeds is the slowest that makes the unanimated
Bullet basketball physically contact the unanimated free Bullet tumbler and tip
it at least 45 degrees by frame 48, while the exact tumbler remains inside the
accepted Preview-96 liquid domain and its measured surface motion requires no
more than eight derived moving-effector subframes?

## Why this gate exists

Attempt-70 closes the 24-frame slow-moving-liquid Preview gate. It does not
justify applying that liquid solve to the retained P02 impact: P02 moves the cup
roughly 7.5-10 cm per frame around contact, many times the `0.009375 m` Preview
voxel. The older launcher screen selected P02 under an arbitrary contact-by-
frame-12 rule rather than a fluid-fidelity rule. This new screen measures the
real cause without paying for fluid.

## Frozen experiment

- Exact source blend and binary remain unchanged.
- The only changed physical degree of freedom is striker `driveEndFrame`:
  `I08=8`, `I10=10`, `I12=12`.
- Cup mass/friction, ball mass/friction, geometry, field gravity, Bullet
  substeps/iterations and striker travel all remain fixed.
- Each candidate receives one independent 48-frame Bullet bake in a fresh
  isolated Blender start.
- Fluid modifiers are removed only in memory. There are zero liquid bakes,
  renders and saves.
- Contact is derived from evaluated cylinder-sphere collision geometry.
- Surface motion uses every exact tumbler mesh vertex, not an object origin or
  hand-entered angular estimate.
- Required effector subframes are
  `ceil(max cup-surface displacement per frame / 0.009375 m)`.
- A candidate must contact by frame 36, reach at least 45 degrees by frame 48,
  keep response after contact, remain on the floor and inside the already
  accepted liquid domain with one-voxel margin, and require at most eight
  subframes.
- If more than one candidate passes, select the largest `driveEndFrame`, which
  is the slowest striker. If none passes, retain the failure and design a new
  preregistered speed interval; do not relax this gate in place.

The exact machine-readable protocol is
`specs/ai-native-studio-rc6-real-impact-bullet-speed-screen.v0.82.json`.
The unique attempt-71 work/evidence roots must remain absent until this
preregistration and its three tools are committed together.

This gate can prove only a bounded Bullet basketball-to-free-tumbler trajectory
and a derived Preview sampling requirement. It cannot prove liquid conservation,
spill, persistence, final-resolution fluid, lighting, camera or film quality.
