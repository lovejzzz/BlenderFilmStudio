# B04 contact benchmark — preregistered protocol

Date: 2026-08-26  
Status: protocol frozen before execution; automated run executed, human review pending  
Target: Blender 5.2.0 LTS, SceneSpec v0.3 candidate, ActorSpec contact contract

## Research question

Can a Blender-compiled character approach, acquire, transport, and release a visible prop while preserving an editable constraint chain and staying inside measurable contact and collision tolerances?

B03 proved that a character socket and a static scene target can agree numerically. B04 must falsify the stronger assumption that this is sufficient for a believable object pickup.

## Why SceneSpec v0.2 is insufficient

SceneSpec v0.2 target sockets are fixed world transforms. During a pickup, the prop socket must move with the prop, and the prop must switch from scene ownership to hand ownership and back. Reusing a static marker would manufacture a passing metric without representing the actual prop.

The minimum v0.3 candidate therefore needs:

1. An asset-bound target socket: `assetRef + objectRef + localTransform`.
2. A contact state sequence rather than one undifferentiated frame range.
3. A restricted constraint instruction with target actor, target bone/socket, influence keys, and inverse policy.
4. Evaluated-geometry pairs for collision inspection.
5. Explicit authorization for `CREATE_CONSTRAINT` and `EVALUATE_GEOMETRY`.

SceneSpec v0.2 remains frozen; B04 must not change its meaning in place.

## Blender 5.2 mechanisms under test

- A Child Of constraint on the prop, targeting the character armature and hand bone.
- Keyframed constraint influence for parent switching.
- A deterministic inverse matrix so enabling the constraint does not create an unintended pop.
- Dependency-graph evaluation for animation, constraints, and modifiers.
- Evaluated meshes converted to BVH trees for overlap pairs and proximity queries.

Blender's manual explicitly identifies animatable Child Of influence as the mechanism for switching parents over time. The API exposes the constraint target, subtarget, influence, inverse matrix, and inverse-recalculation flag. Evaluated geometry must be read from the dependency graph; original mesh data is not evidence of the rendered pose.

## Technical assets

B04 will use deliberately simple, project-owned geometry:

- a separate B04 actor asset derived from the B03 semantic rig;
- visible left and right hand meshes, each fully weighted to its semantic hand bone;
- a rigid prop with a named `GRIP` socket and collision mesh;
- a floor surface with left and right sole targets;
- one arm/hand action and one prop parent-switch track.

The B03 asset will not be modified. B04 receives new binary and semantic identity hashes so previous evidence remains reproducible.

## Preregistered timeline

| State | Frames | Required condition |
| --- | ---: | --- |
| APPROACH | 1–36 | Palm–grip distance decreases monotonically over the final 12 frames; no mesh overlap |
| ACQUIRE | 37–48 | Palm reaches the grip tolerance; Child Of influence changes from 0 to 1 without a transform pop |
| HOLD | 49–108 | Prop follows the palm while the hand transports it by at least `0.30 m` |
| RELEASE | 109–120 | Influence returns from 1 to 0; prop remains at the authored release transform without a pop |
| RETREAT | 121–144 | Palm–prop clearance increases to at least `0.05 m`; no overlap |

The frame ranges and thresholds are frozen before generating the action.

## Automatic metrics

### Contract and identity

- SceneSpec, ActorSpec, prop asset, actor asset, and action library hashes match the BuildPlan.
- Two factory-started builds have identical normalized structure hashes.
- Character semantic identity is unchanged before and after compilation.

### Constraint state

- Child Of target and hand subtarget match the contract.
- Influence is `0` before acquire, `1` during hold, and `0` after release, except inside the declared transition windows.
- Maximum world-space prop discontinuity between adjacent frames is reported; acquire/release pops must be no larger than `0.01 m` and `3°` beyond the authored motion step.

### Contact

- HOLD palm–grip position error: maximum `0.005 m`.
- HOLD palm–grip rotation error: maximum `3°`.
- HOLD relative-transform drift from the first held frame: maximum `0.005 m` and `3°`.
- Transport distance during HOLD: minimum `0.30 m`.

### Geometry

- APPROACH and RETREAT: zero BVH triangle-overlap pairs between visible hand mesh and prop.
- HOLD: overlap-pair count is recorded but is not interpreted as penetration depth.
- Clearance at frame 1 and frame 144: minimum `0.05 m` using evaluated geometry proximity samples.
- Every collision measurement uses evaluated, deformed meshes from the current dependency graph.

`BVHTree.overlap()` returns intersecting triangle index pairs; it does not return penetration depth. B04 v0.1 will therefore report overlap counts and proximity, and will not claim a millimeter-accurate penetration volume.

## Human review

Automatic thresholds cannot prove a believable grasp. A reviewer must answer, without seeing the metric report:

1. Does the hand visibly approach rather than snap?
2. Does the palm appear to support the prop during transport?
3. Is any finger/hand/prop intersection distracting?
4. Is there a visible acquire or release pop?
5. Does the object's weight and motion read coherently?

Machine pass plus human fail remains a failed B04 shot.

## Negative fixtures

The implementation must deliberately reject or fail:

1. Prop socket bound to a missing asset object.
2. Child Of target bone not present in the ActorSpec semantic map.
3. Missing `CREATE_CONSTRAINT` permission.
4. Constraint influence stuck at zero during HOLD.
5. Prop transform pop greater than the threshold at acquire.
6. Hand–prop overlap during APPROACH.
7. Static prop with a fake animated target marker.
8. Evaluation performed on original rather than dependency-graph geometry.

## Stop gate

B04 is not complete until:

- all contract, identity, constraint, contact, and geometry checks pass in two clean builds;
- all eight negative fixtures fail for the intended reason;
- the preview sequence is reviewed by a human;
- the report preserves both machine and human results;
- explicit nonclaims remain visible on the website.

If BVH/proximity metrics cannot distinguish an obvious visual intersection from an acceptable contact, the result is a validator limitation, not a pass. The next experiment must then adopt a stronger signed-distance or collision representation.

## Post-run status (not part of the preregistration)

The executed implementation retained ActorSpec v0.1 because its existing `GRASP` contact window and actor socket were sufficient; the new state and ownership semantics were isolated in SceneSpec v0.3 rather than changing ActorSpec without evidence. This is a documented deviation from the initial v0.2 candidate label, not a silent schema rewrite.

- first automated run: 7/10 checks; 90° grip rotation error, 0.0044 m endpoint clearance, and clear-phase BVH overlaps;
- corrected automated run: 10/10 checks;
- negative fixtures: 8/8 rejected for the intended reason;
- two clean builds: identical normalized structure hash;
- human review: pending;
- experiment complete: false.

Full measurements and deviations are recorded in `research/2026-08-26-b04-contact-experiment.md` and `experiments/contact-v0-1/results.json`.

## Primary references

- [Blender 5.2 manual — Child Of constraint](https://docs.blender.org/manual/en/5.2/animation/constraints/relationship/child_of.html)
- [Blender 5.2 API — ChildOfConstraint](https://docs.blender.org/api/5.2/bpy.types.ChildOfConstraint.html)
- [Blender 5.2 API — Depsgraph evaluated state](https://docs.blender.org/api/5.2/bpy.types.Depsgraph.html)
- [Blender API — BVHTree utilities](https://docs.blender.org/api/current/mathutils.bvhtree.html)
