# RC6 real-impact trajectory restart checkpoint

Date: 2026-09-02

This is a read-only restart checkpoint. It does not preregister or authorize an
experiment, create an attempt-71 root, start Blender, bake Bullet or liquid, or
render media.

## Accepted input

- RC6 attempt-70 is the accepted Preview-96 slow-moving-liquid baseline.
- Preserve particle radius `1.8`, particle band width `4.0`, fractions distance
  `0.25`, and the accepted geometry, Mesh, containment and topology settings.
- Exact source blend:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend`
  with SHA-256
  `9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644`.

## Read-only impact inventory completed before restart

The retained launcher calibration selected P02 because its historical gate
required contact by frame 12. P02 contacts at frame 8 and reaches approximately
90 degrees of cup tilt by frame 15, but its cup translates about 7.5-10 cm per
frame during the impact. That is far larger than the Preview-96 base voxel size
of `0.009375 m`, so directly reusing it would require many liquid-effector
subframes and would be an unnecessarily expensive and fragile first impact
bake.

The same retained screen contains slower candidates that were rejected mainly
by the old early-contact rule: P03 and P05 contact at frame 13, while P06
contacts at frame 17 and still reaches about 62 degrees by frame 24. This is
evidence that the former timing ceiling was not a fluid-fidelity criterion.
It does not select a new trajectory.

## Exact continuation after restart

1. Do not start with a liquid bake or a render.
2. Preregister one Bullet-only speed screen on the exact accepted scene.
3. Change exactly one physical degree of freedom: striker `driveEndFrame`.
   Candidate values `8`, `10`, and `12` are design inputs only until frozen.
4. Keep cup mass, friction, geometry and every non-speed rigid-body property
   fixed. Extend observation to frame 48 rather than preserving the old
   arbitrary contact-by-frame-12 gate.
5. Measure derived contact, solver-owned tilt, stability, and the maximum
   cup-surface displacement per frame. Derive the required liquid-effector
   subframe count from displacement divided by the Preview-96 voxel size.
6. Select the slowest trajectory that still produces genuine ball-to-cup
   contact and at least 45 degrees of solver-owned cup tilt by frame 48.
7. Only after an independent Bullet-only audit passes may the selected impact
   trajectory be combined with attempt-70 liquid settings in a later,
   separately preregistered bake.

No attempt-71 roots or tools existed at this checkpoint. The research branch
and its upstream were both at `cf6b2df06ed3976b92ac473fc22f34d456943ce4`
before this checkpoint commit.
