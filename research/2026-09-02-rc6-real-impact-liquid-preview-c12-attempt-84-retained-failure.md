# RC6 C12 attempt-84 retained failure

Date: 2026-09-02

Verdict: `FAIL_REAL_IMPACT_LIQUID_PREVIEW`

Independent audit: `PASS` 20/20

## What this attempt proved

The first integrated same-solve test combined the accepted R40 Bullet impact
with the accepted attempt-70 Preview-96 APIC liquid settings. The 36-frame run
used the real unkeyed ball and cup, the passive 40 mm-rise ramp, explicit 2 mm
cup collision margin, floor and ramp fluid effectors, and exactly eight derived
effector subframes. It performed one Blender start, one Bullet bake, one Data
bake and one Mesh bake, with zero render, save, native build, network call,
engine source edit or engine remote write.

The rigid-body lineage stayed exact before and after the liquid bake: maximum
cup location error was `5.005858838558197e-9 m`, cup rotation error was `0°`,
and ball location error was `5.122274160385133e-9 m`. Contact remained frame
19; significant spill began frame 20; frame 36 exterior fraction was
`0.9102162`; maximum cup-local centroid shift was `0.2893538423 m`. The liquid
stayed manifold, within the one-voxel domain inset and out of the ramp and world
floor. Maximum deep cup-solid intrusion was `0.0099683`, below the frozen 1%
ceiling.

## Why it failed

Twenty-two of 27 physical checks passed. The five failures were:

- `sourceRelativeVolumeWithin25Percent`
- `temporalVolumeDriftWithin15Percent`
- `positiveLiquidBodiesBounded`
- `connectedComponentsBounded`
- `largestComponentAtLeastHalf`

Frames 1-22 remain physically coherent. Frame 22 is still near source volume
(`0.0014590 m³`) with 18 connected components. The failure begins at frame 23,
four frames after contact: reconstructed volume rises to `0.0034768 m³`, the
mesh splits into 129 components, and 128 positive-volume bodies appear. Peak
source-relative volume error reaches `15.38519449` (about 16.385× source),
temporal drift reaches `13.85306656`, positive bodies reach 239, connected
components reach 243, and the smallest largest-component fraction is
`0.253841`.

This is not a trajectory, obstacle, domain or spill-opportunity failure. It is
a high-speed liquid Data/Mesh stability failure triggered after the real impact.
The accepted slow-motion APIC calibration and eight effector subframes did not
generalize to this free-surface acceleration regime. No render is admissible.

## Immutable evidence

- evidence root: `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84`
- work root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84`
- execution commit: `0f6e7495e991aa11bcebb26a5285c74264ad2de6`
- result self hash: `637089ea884247a60b297dfa4cdab5e487281b38aadc710dc80a7a4dd15124fc`
- receipt self hash: `ca745e230254824e027b67ce7fdaf03c8d1c77e4f61951e50a37014c346b0306`
- independent audit self hash: `bd3b1bc4037a722d04d3501fdc922891aa7948c493e490b206c33a58213d9610`
- work manifest hash: `a7334fff7a3548677b13164cff276cf382ed833fb73ffb9ef06e6caf7d601b5d`
- evidence manifest hash: `89639d7ef41c7174c1058d77f90616ba422b14de83b11edad05c057bd5d3ecc0`
- process wall time: `920.133678 s`
- Data bake: `896.5983414159855 s`
- Mesh bake: `6.554302708012983 s`

Do not repair, rerun or mount this retained cache directly in Blender.

## Next gate

Before any new bake, copy the complete retained cache into one fresh bounded
diagnostic root and compare Data occupancy/support against the already measured
Mesh volume and topology over frames 20-36. The diagnostic must be zero-bake,
zero-render and read-only with respect to attempt-84. Its purpose is to locate
the first failure layer: Data particle/support inflation versus Mesh-only
reconstruction fragmentation. Only after that distinction is measured may one
physical parameter be selected for a new integration attempt.
