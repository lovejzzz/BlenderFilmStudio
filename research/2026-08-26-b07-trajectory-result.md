# B07 immutable baked-trajectory result

Execution date: 2026-08-26

Target: Blender 5.2.0 LTS

Classification: **AUTOMATION PASS / SOURCE PHYSICS NOT APPROVED / FORMAL B07 FALSE**

## Result

One explicitly selected B06 trajectory was exported as a versioned TrajectorySpec containing 132 ordered world-space locations and normalized WXYZ quaternions. The artifact is data-only and includes the exact source evaluation URI, byte hash, source structure hash, frame rate, frame window, tolerances, and an explicit `NOT_HUMAN_APPROVED` status.

- TrajectorySpec SHA-256: `c4efaf29535ca926a5e07014d50d1d4be2007fd5075b148687cb2e81e3caf146`
- source evaluation SHA-256: `90dee5925b528454e90b84d1bef66519224f9ab8e409cf814b3161c9d3dbe4bd`
- replay structure SHA-256 A/B: `0d41d623726acc6f77a84705c683381bd2b0b86e45c5d49e8b96e9974aae1b15`
- maximum 132-frame position replay error: `0 m`
- maximum 132-frame rotation replay error: `0 deg`
- replay prop physics state: no rigid body, parent, constraint, or driver
- negative tests: `8/8` rejected

Compressed `.blend` byte hashes differed. The evidence supports declared replay structure and evaluated transforms, not byte-identical Blender containers.

## Negative evidence

The replay path rejected:

1. wrong TrajectorySpec file hash;
2. a missing sample;
3. a duplicate/out-of-order frame;
4. a non-normalized quaternion;
5. a source evaluation hash mismatch;
6. a rigid body added back to the replay prop;
7. a mutated transform key;
8. an undeclared target object.

## Interpretation

B07 demonstrates the engineering distinction exposed by B06:

1. a physics solver may produce nondeterministic candidate trajectories;
2. a selected candidate can be converted into immutable data;
3. downstream Blender playback of that data can be exact and repeatable.

This does not make the source Bullet solve deterministic. It does not prove the chosen candidate is physically correct, visually acceptable, or approved by a human. The artifact intentionally carries `TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED` so deterministic replay cannot launder an unapproved source into an approved result.

The immutable BuildPlan integration was subsequently completed by B08 (`research/2026-08-26-b08-trajectory-compiler-result.md`). Formal B07 remains false only because visual and authentic human approval of the source solve is still pending.
