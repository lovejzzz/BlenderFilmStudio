# B05 SceneSpec v0.4 compiled grasp result

Execution date: 2026-08-26

Target: Blender 5.2.0 LTS

Final classification: **AUTOMATION PASS / VISIBILITY PASS / HUMAN PENDING**

## Result

The restricted compiler now transforms a hash-pinned SceneSpec v0.4 and GraspSpec v0.1 into a Blender 5.2 scene containing two articulated two-bone IK chains, PoseBone IK limits, two opposed contact targets, keyed prop acquisition/release, and an independent transport target frame.

The final run passed 15 positive machine gates and 8/8 pre-registered negative cases. Two factory-startup builds produced the same structural hash. Their compressed `.blend` byte hashes differed, so the evidence supports structural reproducibility, not byte-identical Blender files.

## Final immutable identifiers

- BuildPlan version: `0.4.1`
- BuildPlan SHA-256: `c245fe10b81c11b8c5fc423cf399b0b74f2a120f038d0bcc662d39092013425c`
- clean-build structure SHA-256 A/B: `a21c1e8944c50e528270cc314afbfe186a8d727ab5fb0dd0b4a8b078b4d315df`
- `.blend` SHA-256 A: `5000cf8e39eaf6633ead2d945e02b451b539dba35092589967789952bef599d7`
- `.blend` SHA-256 B: `c17a782bca95c8edbb39a934272ca4b2518474b4e6c9ce8f1b3b4f4b43187a33`

## Final measurements

- maximum joint-limit violation: `0 deg`
- maximum bone-length ratio error: `2.71095e-7`
- HOLD surface separation: `0.001997984 m`
- minimum active contacts across HOLD: `2`
- opposing normal angle: `179.999991349 deg`
- maximum HOLD relative drift: `1.8e-8 m`
- HOLD transport: `0.300000006 m`
- acquire/release position pop: `0 m / 0 m`
- maximum visible segment-to-pose alignment error: `4.5e-8 m`

The authored active-camera visibility diagnostic also passed:

- fingers: minimum in-frame `1.0`, minimum visible `0.9166667`, median visible `0.9166667`
- prop: minimum in-frame `0.5`, minimum visible `0.5`, median visible `1.0`

## Falsification and correction trail

### First run: unreachable contact targets

The first pre-registered build compiled successfully but failed contact evaluation. The original 0.12 m finger chains could not reach the frozen opposed targets; HOLD separation was `0.044024683 m`, so active contacts were `0/2`. The failed evaluation and BuildPlan are preserved under `experiments/grasp-v0-2/B05.first-run-falsified-*`.

The asset correction increased each two-bone chain to 0.18 m. Acceptance thresholds and GraspSpec contact coordinates were not changed.

### Second audit: numerical pose passed while visible meshes failed

The corrected chain passed the original numerical gates, but rendered frame 78 showed the prop moving upward while the visible finger meshes remained behind. The compiler had animated the armature object rather than the full technical-character asset root. Pose-bone contact values were therefore correct while rendered geometry was wrong.

That pre-visual-audit result is preserved as `experiments/grasp-v0-2/B05.pre-visual-audit-results.json` and must not be cited as final. Compiler behavior version 0.4.1 now transports the character root, and gate C15 compares every evaluated finger-segment centroid against the corresponding evaluated pose-bone midpoint.

## Negative evidence

All pre-registered defects were rejected at the intended layer:

1. unsupported generic joint-limit source — BuildPlan rejection;
2. invalid joint range — semantic rejection;
3. non-opposed contact normals — semantic rejection;
4. missing declared finger bone — Blender compile rejection;
5. missing `CREATE_GRASP` authorization — BuildPlan rejection;
6. runtime stretch enabled — IK-contract rejection;
7. one HOLD contact disabled — active-contact rejection;
8. one HOLD target displaced — drift rejection.

## What this establishes

This experiment establishes a reproducible restricted path from declared grasp semantics to evaluated Blender kinematics and visible technical geometry. It also establishes that pose-only evaluation is insufficient; evaluated render geometry must be checked explicitly.

It does not establish force closure, frictional support, collision response, dynamics, anatomical realism, skin deformation, material realism, acting quality, or final human acceptance. The prop follows a declared keyed Child Of constraint after acquisition; the fingers do not physically support it.

The benchmark remains incomplete until at least three authentic independent reviewers complete the locked visual rubric. No responses may be fabricated.
