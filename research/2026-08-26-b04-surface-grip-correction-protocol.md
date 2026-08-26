# B04 surface-grip correction — preregistered protocol

Date: 2026-08-26

Status: frozen before execution

Base: B04 SceneSpec v0.3 and unchanged actor, prop and Action binaries

## Failure mechanism

The original `GRIP` target and `PALM_R` effector both represented object centres. Constraining those frames to coincide guaranteed volumetric hand/prop intersection even when the socket error was zero.

## Correction

Create an independent SceneSpec fixture (`SHOT_105`) without modifying the original B04 input or evidence:

- keep actor, prop, Action, constraint timing, camera, lights and output policy unchanged;
- move the prop-local `GRIP` target to `[0, 0, -0.232] m`;
- interpret this as a palm-centre contact shell: prop half-extent `0.17 m` + hand half-thickness `0.06 m` + `0.002 m` diagnostic clearance;
- move the authored prop root at acquire and release so the offset `GRIP` still matches the evaluated palm socket;
- regenerate SceneSpec and BuildPlan hashes.

The 2 mm clearance is declared before execution. It is not selected after observing the geometry report.

## Gates

1. SceneSpec v0.3 and BuildPlan validation pass.
2. Two clean builds produce the same normalized structure hash.
3. The original 10 contact checks pass.
4. Eight original negative fixtures remain rejected by the unmodified compiler/validator experiment.
5. Geometry diagnostic v0.2 reports:
   - zero HOLD frames with tessellated surface overlap;
   - maximum HOLD inside-vertex depth `0 m`;
   - minimum HOLD exact unsigned surface separation between `0.001 m` and `0.003 m`.
6. Original B04 hashes and reports remain available and unchanged as the falsified centre-grip baseline.
7. Human review remains separately required; geometry correction is not visual acceptance.

## Nonclaims

- A rigid box contact shell is not a finger grasp.
- Two millimetres of geometric clearance is not pressure, friction or support force.
- Passing this correction does not establish weight, anatomy, soft tissue or performance quality.

## Post-run result (not part of preregistration)

The correction failed its geometry gate:

- original 10 checks: passed;
- HOLD surface overlap: 60/60 frames;
- HOLD maximum inside-vertex depth proxy: `0.018445877 m`;
- required HOLD separation: `0.001–0.003 m` — not achieved.

The declared `0.232 m` shell assumed the visible hand box axes matched the palm bone/socket axes. They do not: the hand mesh coordinates were baked in actor/world rest space, while the socket rotation inherited the angled `hand.R` bone frame. The offset moved the prop along the bone-local Z axis, but the visible hand's support radius along that world direction was larger than the assumed `0.06 m` half-thickness.

This failed variant is preserved as `specs/benchmarks/B04.surface.scene.json` with evidence under `experiments/contact-v0-2/`. The next correction must align the semantic socket frame with visible hand geometry before applying a contact shell.
