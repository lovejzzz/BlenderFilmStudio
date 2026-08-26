# B05 two-finger IK feasibility spike — preregistered protocol

Date: 2026-08-26

Status: frozen before Blender execution

## Scope

Test whether Blender 5.2 can deterministically construct, solve and evaluate a minimal two-finger articulated gripper using actual bone IK limits. This is an implementation spike below the formal SceneSpec → BuildPlan compiler and is not a B05 benchmark pass.

## Locked scene

- Two finger chains: thumb and index, two bones each, `0.06 m` per bone.
- Each chain uses one IK constraint with `chain_count=2`, no stretch, and a declared target Empty.
- All four pose bones use Z-axis IK limits matching `B05.grasp.json` and nonzero IK stiffness.
- Two fingertip proxy spheres have radius `0.01 m`.
- Convex box prop has X half-extent `0.05 m`.
- Target tip centres close to X=`±0.061 m`, representing `0.001 m` fingertip-to-prop surface separation.
- Closure: frames `37–48`; HOLD: `49–108`; release: `109–120`.
- A common carrier moves the entire technical assembly `0.30 m` during HOLD. This tests constrained evaluation and relative stability, not contact-driven dynamics.

## Gates

- two clean script builds produce byte-identical normalized structure manifests;
- all expected bones, IK constraints and targets exist;
- every pose bone reports `ik_stretch=0` and evaluated length ratio differs from 1 by at most `1e-6`;
- no evaluated joint exceeds its declared IK range by more than `0.1°`;
- both fingertip surface separations remain in `[0.0005, 0.0015] m` throughout HOLD;
- tip-to-prop relative drift during HOLD is at most `0.0001 m`;
- carrier transport is at least `0.299 m`;
- target distance is monotonic over the 12 closure frames.

## Nonclaims

The prop shares a carrier with the gripper. Passing cannot establish contact-driven support, force closure, friction, collision-free full finger meshes, human anatomy, skin deformation, weight or visual credibility.
