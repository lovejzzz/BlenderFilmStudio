# RC6 C15 result — residual transition order remains intentionally inconclusive

C15 is a valid zero-Blender diagnostic and its independent audit passes 22/22.
It copied all 108 retained C14 cache files (18,032,601 bytes) into a fresh root,
reopened all 36 particle/velocity VDB metadata records and decoded the saved
configuration metadata. The retained source cache was byte-exact before and
after the run.

The strict classification is `TRANSITION_ORDER_INCONCLUSIVE`:

- C12 Data and Mesh first expanded together at frame 23.
- With C14 `timesteps_max=8`, cup-solid Mesh intrusion first exceeded 1% at
  frame 31 and peaked at 2.453988% on frame 32.
- Velocity occupied support exceeded the 25% comparison line at frame 34.
- Mesh volume, source conservation, temporal drift and positive-body count
  first failed at frame 35.
- Particle occupied support exceeded 25%, and connected components exceeded
  32, at frame 36.
- Across frames 20–36, particle-support/Mesh-volume correlation is
  `0.99914717`; velocity-support/Mesh-volume correlation is `0.98725241`.

The frozen classifier required particle support to cross no later than Mesh.
Because Mesh crossed one frame earlier, the evidence is not relabeled after the
fact. The sequence nevertheless rules out a clean Mesh-only story: velocity
support rises before the Mesh failure and particle support then expands by
166.32% as Mesh expands by 238.33%.

Saved terminal substeps range from 0.00715346 s to 0.03176064 s. The frame-36
value, 0.01312088 s, is close to the theoretical regular-step floor of
0.01302083 s for eight maximum steps, but the saved value is only the terminal
substep. It is not a complete adaptive-step roster and cannot prove that the
solver used exactly eight steps.

Evidence:

- root:
  `experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87`
- result self hash:
  `f1940fd7246ae859b53234635b0114d4aadff47f42e963c5c51b3b193c9f9b61`
- receipt self hash:
  `371614c5117a8bd74297249755d8974f667b1ffaedb84b98a87beccb1b6bf974`
- independent audit self hash:
  `826beb9fba4e80f7a1c1cb581c77e686f5dea02fb80322f393cf72ad6949173a`
- final evidence manifest self hash:
  `4681c0315baa8b2ac357e11d1546051014676b11c2d6e81f3042d5cd90e64a7b`

Counts including audit are two engine-Python starts and zero Blender starts,
bakes, renders, saves, network calls or retained-root writes.

The next test must remain a single simulation variable. Bound source inspection
selects `cfl_condition` 2.0→1.0 while retaining `timesteps_max=8`: Blender's
RNA describes CFL as maximum velocity per cell, and Mantaflow scales adaptive
`dt` with CFL before clamping it to the frozen min/max bounds. This tests whether
finer adaptive sampling before the ceiling prevents the velocity-field rise. It
does not assume the observed terminal `dt` proves the cause.
