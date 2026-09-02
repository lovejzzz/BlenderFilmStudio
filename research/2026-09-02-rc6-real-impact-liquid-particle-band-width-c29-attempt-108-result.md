# RC6 C29 result — Narrower band suppresses growth by losing support

Date: 2026-09-02
Physical verdict: `FAIL 25/27`
Independent audit: `20/20 PASS`

C29 changed exactly one physical property on exact C18:
`particle_band_width 4.0 -> 3.0`. One RC5 Blender process completed the exact
36-frame R40 Bullet trajectory, one Preview-96 Data bake and one Mesh bake.
It rendered and saved nothing.

The narrower continuing resampling band removed the prior fragmentation and
late volume-gain failures:

- maximum positive liquid bodies improved from `37` to `10`;
- maximum connected components improved from `37` to `10`;
- maximum source-relative error improved from `47.217%` to `41.561%`;
- cup, ramp, floor and domain intrusion remained zero;
- first significant spill moved from frame `24` to `26`;
- frame-36 exterior liquid fell from `48.043%` to `20.572%`.

It did not conserve liquid. C18's frame-1 reconstructed Mesh was `10.315%`
above the frozen source and later expanded. C29 began `3.992%` below source,
fell to `41.561%` below source at frame 36 and drifted `39.131%` from its own
frame 1. Thus the change replaces explosive support growth and fragmentation
with a much cleaner but steadily shrinking liquid. The only two failed frozen
checks are source-relative volume within 25% and temporal drift within 15%.

This is real regime sensitivity. Width `4.0` remains the accepted slow-tip
value, where it reduced temporal loss to `6.902%`; width `3.0` is cleaner under
this high-speed impact but loses too much material. Neither may be taught as a
universal product default. The next bounded step is a zero-Blender copied-cache
C30 comparison of C29 against C18, measuring particle and velocity support
alongside Mesh to confirm whether the monotonic loss begins in Data before any
new physical variable is selected.

Runtime and bindings:

- Data bake: `1134.060 s`; Mesh bake: `4.414 s`;
- process wall time: `1145.640 s`;
- exact cache roster: `108` files;
- workspace/evidence: about `14 MiB` / `184 KiB`;
- execution commit: `1a805e998fb1f8e7b96e1d1a51691d698d19357f`;
- spec hash: `1435c0b09673366ed76418923c536ce5ac1f4213b093d8a75181bc2e376f42b9`;
- result hash: `6b78c2fabf4f98bf0cf7e389a815293c7765eadf7400eb029b7552a9842bb3b8`;
- receipt hash: `dd620c78f0c6e7b9c2675a938dbc16af4c13d8c26148656ddde93a1151c55f26`;
- independent-audit hash: `14b5536e6119226f1c3098129336969347f3c3c3534865d22967cb0cdc0f9b35`;
- work/evidence manifest hashes: `e5ffffce1df5af6eff0efb13e0d6f5d679f154444378418c6a01a95843314b69` /
  `716974cae6599c0003ef9143424e9a4e6bdc3d24fd3a18cf107b50c2d1ac96c8`.

Retain attempt-108 unchanged. Do not rerun C29, test a second band width,
combine widths, render this failed liquid or reinterpret lower spill as
conservation.
