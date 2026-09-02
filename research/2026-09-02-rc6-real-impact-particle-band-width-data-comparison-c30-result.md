# RC6 C30 result — Narrow-band cleanup is Data-layer support loss

Date: 2026-09-02
Diagnostic verdict: `PASS 8/8`
Independent audit: `23/23 PASS`

C30 started no Blender process and changed no retained result. It copied all
`108` immutable C29 cache files into one fresh bounded root, reopened every
frame with the accepted engine Python runtime and compared signed particle,
velocity and Mesh support against the better C18 baseline.

The classification is `PARTICLE_AND_MESH_SUPPORT_LOSS`:

- frame `22` is the last coherent comparison baseline;
- C29 particle occupied support crosses `-15%` at frame `26`;
- C29 reconstructed Mesh crosses `-15%` at frame `31`, five frames later;
- velocity occupied support never crosses `-15%` and instead first expands at
  frame `26`;
- minimum particle/Mesh/velocity drift is `-44.172% / -31.560% / -13.463%`;
- particle support and Mesh volume are strongly correlated (`r=0.961341`),
  while velocity support and Mesh are not (`r=-0.075800`).

C18 shows the opposite response: it has no `-15%` particle, velocity or Mesh
loss crossing, but expands at frames `25/24/24` and reaches maximum positive
particle/velocity/Mesh expansion of `32.384% / 173.840% / 51.544%`. C29 has no
positive particle or Mesh expansion above the frozen `25%` line. Its physical
temporal-volume failure starts at frame `25`, particle-support loss at frame
`26`, source-relative-volume failure at frame `30`, and Mesh-support loss at
frame `31`; topology and intrusion never fail.

This closes scalar `particle_band_width` tuning. Width `3.0` really suppresses
the high-speed width-`4.0` growth and fragmentation mode, but does so alongside
Data-layer particle-support loss that precedes the visible Mesh loss. The
velocity grid does not explain the shrinking surface. Occupied support is not
exact liquid mass, so C30 does not identify one Mantaflow operation and does
not authorize an adaptive setting. The software must learn that the same
setting has opposite useful directions in slow-tip and impact regimes; a
regime policy requires a preregistered independent holdout before product use.

Runtime and bindings:

- copied cache: `14,050,289` bytes; producer wall time `0.110484 s`;
- total starts: two engine-Python processes; zero Blender, bake, render, save,
  network or retained-root writes;
- execution commit: `4dfc9108a14581662576f8647076bce3d962f5c1`;
- spec hash: `b3450b0d21087f0c19e99cb7b7de66c07375639bbb2d037791d69134dfe379ba`;
- result hash: `09c46e1644f358f9df102d3a0338e68d8805ad30583a4b60369a3df709ae1b35`;
- receipt hash: `f3645b496c0ee9de8a6aab8aaafac30dad5e7252a0d6df24d923ccf3d69065c5`;
- independent-audit hash: `fd50591945269660c92cc058e75af1656cdfd171b06cac3e38ce656950135b6d`;
- work/evidence manifest hashes: `d40155db4d9187dda5f5ee8157a0e1a8f3d641aeddaac498b4407e720906bab4` /
  `ded39e30d6affaea21a701a8f2118a2c3052740ec9446022c56883f39d357ed1`.

Retain attempt-109 unchanged. Do not rerun C30, test another band width, render
the failed liquid or teach width `3.0`/`4.0` as a universal default. After a
restart, the next bounded gate is C31: zero-Blender read-only design of a small
event-regime feature and decision-policy contract from retained evidence. It
must define an independent holdout before any adaptive product mutation or new
physical bake.
