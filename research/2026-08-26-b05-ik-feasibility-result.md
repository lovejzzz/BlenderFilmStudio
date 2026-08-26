# B05 two-finger IK feasibility spike — result

Date: 2026-08-26

Status: **FEASIBILITY PASS · FORMAL B05 BENCHMARK NOT PASSED**

## Reproducible result

Blender 5.2.0 LTS constructed and evaluated two independent two-bone finger chains with actual IK constraints, per-bone Z-axis IK limits, stiffness and stretch disabled.

- Normalized structure SHA-256 A/B: `86ae7ec3287cbe57c3dce23e7d448b379108cf2cfec12959066998ab58d23385`
- Manifest file SHA-256 A/B: `e0be6702362388b8a067a34e3deed581fa155f02cf7c26f400cc6a4013954248`
- Evaluation report SHA-256 A/B: `865157c92837fae0a962786b93e581878a2aabaadafb37df8634746622176088`
- Binary `.blend` files differed, as expected from the existing reproducibility boundary.

## Measurements

- maximum joint-limit violation: `0°`;
- maximum evaluated bone-length ratio error: `1.00995e-7`;
- maximum HOLD fingertip-to-IK-target error: `0.000009034 m`;
- HOLD fingertip surface separation: `0.001000011 m` for both sides;
- HOLD fingertip-to-prop relative drift: `0 m`;
- HOLD carrier transport: `0.300000006 m`;
- 12-frame closure distance decreased monotonically from `0.099954217 m` to `0.000018068 m`.

All ten preregistered feasibility gates passed in both clean builds, and the full 120-frame evaluation reports were byte-identical.

## What this changes

The spike shows that Blender 5.2 exposes enough deterministic control and evaluation state for a compiler to build finger chains, apply correct IK-limit semantics, forbid stretch and measure a multi-contact closure. This justifies implementing formal GraspSpec → BuildPlan instructions instead of treating finger articulation as an untestable research idea.

## What it does not change

The prop and gripper share a common animated carrier. The scene therefore does not prove contact-driven support, force closure, friction or dynamics. It is also a standalone builder rather than the immutable BuildPlan compiler, has no runtime negative fixtures, and has not undergone human review. The formal B05 benchmark remains false.
