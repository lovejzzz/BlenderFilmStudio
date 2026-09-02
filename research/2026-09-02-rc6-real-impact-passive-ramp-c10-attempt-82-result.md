# RC6 real-impact passive-ramp C10 attempt-82 result

Date: 2026-09-02

C10 is a retained physical `FAIL` with an independent 23/23 audit. Reducing
only ramp rise from 60 to 40 mm produced the intended minimum raised contact:

- ball center at contact: 0.38175 m, PASS;
- contact: frame 19; response over 5°: frame 21;
- first 45°: frame 32; peak tilt: 90.15°;
- floor gate: PASS;
- full-window maximum surface motion: 99.39 mm/frame at frame 38;
- full-window derived subframes: 11, FAIL;
- accepted-domain containment: FAIL, swept max x=1.00394 m.

Ramp-height response is non-monotonic after tipping: R40 has lower contact than
R60 yet a slightly larger landing-step peak. Close ramp-height tuning rather
than interpolating again.

The retained samples expose a separate product question. At frame 36 the cup
first reaches 70.04°, maximum surface motion so far is 72.10 mm/frame (eight
Preview-96 subframes), and swept max x is 0.96482 m. A same-size 0.90 m domain
centered at x=0.57 would contain the initial through first-70° sweep with more
than one voxel margin. A future audit-only gate may recompute this exact
contact-to-first-70° event window from retained samples. It must not rewrite
C10, claim that all liquid has spilled, or start Blender.

Counts were one Blender start, one Bullet bake and zero liquid, render, save,
build, network and engine-write operations. Result/receipt/audit self hashes
are `9deeebd3...` / `289eebcb...` / `8b6b1812...`.
