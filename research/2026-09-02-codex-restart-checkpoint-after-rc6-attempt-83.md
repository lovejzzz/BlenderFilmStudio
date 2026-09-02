# Codex restart checkpoint after RC6 attempt-83

Date: 2026-09-02

This is a handoff checkpoint only. It does not preregister or start another
Blender, Bullet, Mantaflow, render, save, build, network or repository
experiment.

## Durable state

- Research `main` is committed and pushed through
  `80dcae3c92b487b9bfa0d5612dc6ad30f87ef7e4` before this checkpoint.
- The long-running product goal remains active: build a complete real project,
  improve it through screenshot-led visual judgment, teach the product reusable
  filmmaking rules, and accumulate those rules in the
  `physical-film-direction` skill.
- Exact accepted source scene:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46/final-effector-mesh-c3/source-state.blend`,
  SHA-256 `9ac79c9c3c0d13273ac20804a3af99884f9465534800c3d9ca2ae8121499e644`.
- Exact admitted existing binary:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender`,
  SHA-256 `ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2`.
- Latest host preflight reported about 155 GiB free, below the conservative
  160 GiB admission threshold for another clean native build. The accepted
  existing binary may continue under the standing resource bounds.

## Closed impact-trajectory investigation

The corrected 2 mm cup collision margin is permanent for this branch of the
experiment. The former 90-degree I09 result under the implicit 40 mm margin was
a collision-scale artifact and must not be restored for drama.

Subsequent single-variable tests are all retained, audited results:

- C7-C1 attempt-79: 14% more striker speed raised tilt only 2.67 to 3.19
  degrees while raising surface motion 34.66 to 40.83 mm/frame and the sampling
  requirement four to five subframes. Striker-speed tuning is closed.
- C8 attempt-80: raising the combined cup-floor friction from 0.435 to 0.464
  reduced sliding slightly but raised tilt only to 2.98 degrees. Friction
  coefficient tuning is closed.
- C9 attempt-81: a real passive 300 mm run / 60 mm rise ramp raised the unkeyed
  ball and produced a causal 90-degree tip, but later fall motion required ten
  subframes and left the domain.
- C10 attempt-82: reducing only the ramp rise to 40 mm preserved the causal tip,
  but the full 48-frame fall/landing remained non-monotonic and failed at eleven
  subframes plus domain escape. Ramp-height tuning is closed.
- C11 audit-only attempt-83: the immutable R40 trajectory's derived frame
  1 through first-70-degree frame 36 window passes 16/16. It contains contact at
  frame 19, requires eight Preview-96 effector subframes, and fits with one
  voxel margin in the unchanged 0.90 x 0.50 x 0.58 m domain translated to
  x=0.57. The full 48-frame trajectory remains FAIL.

Attempt-83 evidence:
`experiments/physical-richness/RC6-2026-09-02-real-impact-event-window-c11-attempt-83`.
Its independent audit self hash is
`96a159ccbcb418df15eeba0af1e54c4bd8ba98c326824b8b319fcc0e0f427891`.

## Performance conclusion

The observed first ten Final-192 liquid frames taking about 32 minutes is
consistent with retained measurements on this M2 Max, not evidence of a broken
computer. Resolution 96 to 192 multiplies the base voxel count by roughly eight
before solver, particles, meshing and cache I/O. Almost all prior cost was
Mantaflow Data/Mesh baking, not final rendering. Final-192 remains a final
validation tier; Preview-96 is the development tier.

## Exact next gate

`RC6-REAL-IMPACT-LIQUID-PREVIEW`

Preregister and implement one integrated same-solve preview with these frozen
causal ingredients:

1. Use the R40 passive ramp and I09 pusher from attempt-82; the ball and cup
   remain unkeyed and solver-owned.
2. Use frames 1-36 only, ending at the derived first-70-degree event boundary.
3. Use the same-size liquid domain centered at x=0.57 and eight derived moving
   effector subframes.
4. Bind all accepted attempt-70 Preview-96 APIC liquid settings, including
   particle radius 1.8, particle band width 4.0, fractional distance 0.25,
   mesh radius 2.5, mesh scale 2, and the frozen conservation/mesh controls.
5. Preserve the source static-liquid cache byte-exact by rebinding a unique
   fresh modular cache before any reset or bake.
6. Add explicitly frozen static Mantaflow effector semantics for the floor and
   passive ramp as well as the moving cup. Without floor/ramp liquid collision,
   cap the claim at `LIQUID_EXITS_CUP_IN_DOMAIN`; do not call it a physically
   supported spill.
7. In the same Blender process, bake the real Bullet trajectory once, verify
   it against the retained R40 samples, then bake Mantaflow Data and Mesh from
   that preserved solve. Do not substitute the old hinge/motor slow-tip rig and
   do not replay authored cup transforms.
8. Independently audit exact process counts/cache roster, full-window liquid
   volume/topology, below-floor intrusion, domain containment, and a
   preregistered post-contact spill-opportunity signal. A physically honest
   FAIL is acceptable; do not tune thresholds after seeing output.
9. Do not render or start Final-192 until this integrated physical preview and
   its audit pass. A future visual review must use actual screenshots, not
   numeric evidence alone.

## Restart order

1. Read `AGENTS.md`, `START_HERE.md`,
   `handoff/ai-native-studio-current-state.v0.1.json`, this checkpoint, and the
   complete `physical-film-direction` skill.
2. Run `node scripts/preflight-f0-source-host.mjs`.
3. Confirm the research worktree is clean and `HEAD == origin/main`.
4. Finish the read-only integrated-tool inspection, then freeze a versioned
   C12 specification, preregistration, runner and independent auditor before
   creating a fresh attempt root or starting Blender.

No C12 experiment root, Blender start, liquid bake or render exists at this
checkpoint. Retain attempts 77 through 83 and all earlier evidence unchanged.
