# RC6 C27 result — Water diffusion delays onset but worsens late amplitude

Date: 2026-09-02
Status: `PASS_DIAGNOSTIC`; independent audit `23/23 PASS`
Classification: `MIXED_ONSET_AMPLITUDE_RESPONSE`

C27 copied all 108 immutable C26 cache files, measured every frame with the
accepted engine Python/OpenVDB runtime, and independently reproduced the result.
The source-cache manifest stayed exact at `7a512ae4…`; no retained root changed.

Against exact C18, the 25% expansion crossings moved later:

- velocity support: frame 24 → frame 34;
- Mesh volume: frame 24 → frame 34;
- particle support: frame 25 → frame 36.

That delay is not a stability win. C26 had already lost 17.098% of frame-1 Mesh
volume at frame 21, before those positive-expansion crossings. At frame 36 the
maximum expansions were all worse:

- velocity support: 173.840% → 201.674%;
- particle support: 32.384% → 75.694%;
- Mesh volume: 51.544% → 95.003%.

Particle support and Mesh remain strongly correlated (`r=0.99072`); velocity
support and Mesh correlate at `r=0.96871`. Occupied support is still not exact
mass and does not identify one internal Mantaflow operation. Together with the
physical result—temporal failure advancing to frame 21, significant spill
delaying to frame 34, and worse conservation/fragmentation—this closes Water
diffusion as a useful correction. Do not scan viscosity or add surface tension.

Evidence identities:

- execution commit: `461706e8…`;
- result self hash: `6a3847a9b3f9f239796fc08cda12512c9e3c926ada480fb8c011eeae455614b7`;
- receipt self hash: `7937eba8ba27a856d79de87b263ea60add86162d946faad953432316ebd2f4ee`;
- audit self hash: `5918981f7f81dbad6f389915471c85bf0ba306303664ee84a663e0d3b8459149`;
- copied-work manifest: `bffce90799c953af434c351cd49d14694ed81e515d39a6791395c9a081f37513`;
- final evidence manifest: `ad5588f77c690f01e418724faf0294f64e5d13dce240c174fb921b76ce820040`.

Total operations were two engine-Python starts and zero Blender, Bullet, Data,
Mesh, render, save, build, network or retained-root writes. The next gate is one
read-only source/configuration inspection that selects exactly one distinct
Data-layer degree of freedom on the materially better C18 baseline. No physical
mutation or render begins before that selection is frozen.
