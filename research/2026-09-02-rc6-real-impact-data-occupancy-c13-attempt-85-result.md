# RC6 real-impact Data occupancy C13 attempt-85 result

Date: 2026-09-02

Verdict: `PASS_DIAGNOSTIC`

Classification: `DATA_SUPPORT_EXPANDS_WITH_MESH_MESH_ONLY_CAUSE_REJECTED`

## Result

The complete 108-file C12 cache was copied into a fresh bounded root and all
36 Data frames were reopened with the accepted engine's OpenVDB runtime. The
retained source cache remained byte-exact. The runner and independent auditor
used two engine-Python starts total and zero Blender starts, bakes, renders,
saves, network calls or retained-root writes.

Frame 22 is the last coherent baseline. At frame 23:

- particle occupied support rises 1,554→2,973 voxels (`+91.31%`);
- velocity occupied support rises 17,829→76,749 voxels (`+330.47%`);
- retained Mesh volume rises `+138.29%` from frame 22.

The first Data and Mesh expansion frames are both 23. Across frames 20–36,
particle occupied support and Mesh volume correlate at
`0.9759746037621211`. Maximum growth relative to frame 22 is `+1077.93%` for
particle support, `+908.19%` for velocity support and `+1391.72%` for Mesh
volume.

This rejects a Mesh-only reconstruction explanation: the gross expansion is
already present in the Data cache. Occupied sparse voxels are not exact mass,
so this result does not yet identify the specific solver mechanism. Mesh-radius
or smoothing changes are not an admissible physical correction.

## Evidence

- evidence root: `experiments/physical-richness/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85`
- work root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-data-occupancy-c13-attempt-85`
- execution commit: `d02fc6f2634f3f40af202e54e7709ef6d4181d23`
- result self hash: `64bee342cee49afac6726413615f3726437ac587801c0bae22f0c1e0422ce542`
- receipt self hash: `4920de2dec0d0fd2a81b393bfee0179083c5685076ab723724c781f9aa8b29c2`
- independent audit: 22/22 `PASS`
- audit self hash: `ab91f5076ef643c130913d4d00f2a57e3885ae78f65e41df965d8d7ed0d2489c`
- retained cache manifest: `07d19e6f9ee41ddb5ff837db31373bd6119c5a55b5bb217414835895b1bf5207`
- copied cache manifest: `43dd00236e8540d33ca79cde8c836fef58f8f436ee28b8b7d00a156c1c5f4940`

## Next gate

Inspect the bound Mantaflow source and exact C12 configuration read-only to
select one high-speed Data-layer degree of freedom. Preserve the R40 Bullet
trajectory, geometry, domain, liquid source, resolution, reconstruction and
all physical thresholds. Do not bake or render before that single-variable
hypothesis is preregistered.
