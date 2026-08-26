# B04 socket-frame correction — preregistered protocol

Date: 2026-08-26

Status: frozen before execution

Base: original B04 actor asset and Action binaries; new ActorSpec/SceneSpec fixtures only

## Hypothesis

The surface-grip correction failed because the semantic palm socket frame and visible hand proxy frame disagree. If `PALM_R` is rotated by the inverse hand-bone rest rotation, its evaluated world frame will align with the world-axis-aligned visible hand box. A prop-local contact shell can then separate the two boxes without breaking socket equality or parent switching.

## Locked correction

1. Copy the original ActorSpec to `B04.socket-frame.actor.json`.
2. Keep asset, rest pose, topology, action and contact window unchanged.
3. Change only `PALM_R.offset.rotationEulerDeg` to `[29.205923042, 23.57817843, -77.395619221]`.
4. Copy the original SceneSpec to `B04.socket-frame.scene.json` and update the ActorSpec hash reference.
5. Set prop rotation to identity.
6. Set prop-local `GRIP` to `[0, 0, -0.232] m`, equal to `0.17 m` prop half-height + `0.06 m` hand half-height + `0.002 m` diagnostic clearance.
7. Place the prop root so `GRIP` equals the evaluated palm at acquire and release.
8. Do not change Action, constraint influence keys, compiler, contact evaluator, geometry diagnostic or thresholds.

## Gates

- ActorSpec and SceneSpec validators pass.
- Two clean builds have identical normalized structure hashes.
- Original 10 contact checks pass.
- Geometry v0.2: HOLD overlap frames `0/60`, maximum inside-vertex depth `0 m`, minimum exact unsigned separation `0.001–0.003 m`.
- Socket world rotation error during HOLD remains `≤ 3°`.
- Original centre-grip and failed bone-axis surface-grip fixtures remain reproducible.
- Human review remains pending and must use a newly hashed clip if this correction is rendered.

## Nonclaims

This tests coordinate conventions and rigid proxy separation. It does not test fingers, force closure, pressure, friction, soft tissue, object mass, weight perception or actor-quality motion.
