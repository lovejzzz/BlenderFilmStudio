# B06 contact-driven rigid-body support result

Execution date: 2026-08-26

Target: Blender 5.2.0 LTS

Final classification: **CONTACT-LIFT FEASIBILITY PASS / REPRODUCIBILITY FAIL / FORMAL B06 FALSE**

## Question and answer

A 0.25 kg active rigid-body prop can be lifted approximately 0.30 m against gravity by two independently animated passive colliders using only Bullet collision and declared friction. The prop has no parent, Child Of, rigid-body constraint, transform-copy constraint, driver, or transform animation during HOLD.

That narrow feasibility result is positive. The formal benchmark is negative because repeated fresh Blender processes do not produce a sufficiently reproducible full release trajectory.

## Final positive configuration

- Blender 5.2.0 LTS rigid bodies;
- 0.10 × 0.12 × 0.14 m prop, 0.25 kg;
- two 0.04 × 0.24 × 0.18 m passive animated colliders;
- friction assumption 1.0;
- collision margin 0.0002 m;
- 240 substeps per frame, 40 solver iterations;
- linear damping 0.8, angular damping 0.95;
- gravity `(0, 0, -9.81)` m/s²;
- structure SHA-256 `e18e4d1d15f9f97890354ce5807f4bdce6ed9c74b507e17c8df0c77d14fdfb6e`.

## Positive measurements

- vertical transport: `0.300012082 m`;
- maximum HOLD collider-midpoint drift: `0.000898925 m`;
- HOLD rotation change: `0.309010138 deg`;
- maximum centre-axis escape: `0.000709679 m`;
- release fall by frame 132: `2.909608796 m`;
- maximum collider step: `0.006500005 m/frame`;
- maximum collision margin: `0.0002 m`.

All 11 individual positive checks passed. All 8 pre-registered negative classes were rejected: zero friction, one collider, insufficient closure, prop kept kinematic, forbidden parent, teleporting colliders, excessive margin, and inadequate substeps.

## Falsification trail

### First run: energy injection and edge escape

The original side faces matched the prop depth and began with roughly 2 mm penetration. On the first dynamic frame the prop escaped laterally, accumulated nonphysical energy, fell `14.601222029 m` by the HOLD endpoint, and rotated `162.96157903 deg`. This run is preserved in `B06.evaluation.json`.

The correction widened the side faces, reduced the initial overlap and collision margin, and maintained a small inward squeeze. Acceptance thresholds did not change.

### False confidence from two-run tests

Some two-run executions produced identical trajectories; other executions with the same declared structure produced more than 0.10 m divergence after release. A single A/B run was therefore not an adequate reproducibility test.

The final audit used 10 independent factory-startup builds and all 45 pairwise trajectory comparisons:

- unique declared structure hashes: `1`;
- all 10 individual runs passed their positive gates;
- maximum HOLD divergence: `0.000370306 m` at frame 49;
- maximum release/full divergence: `0.106824989 m` at frame 132;
- frozen threshold: `0.001 m`;
- reproducibility gate: **FAIL**.

Removing floor impact from the observation window eliminated one source of chaotic branching but did not make post-release Bullet trajectories reliably deterministic across fresh processes.

## Interpretation

This experiment establishes that Blender can produce contact-driven rigid-body transport for one declared configuration without a transform-following shortcut. It also establishes that identical scene structure and individually plausible trajectories are insufficient evidence of cross-process physics reproducibility.

The next defensible workflow is `solve → inspect → select canonical cache/bake → hash the baked trajectory → use that immutable trajectory downstream`. This can make production playback repeatable, but it does not make the original solver deterministic and must not be described that way.

Formal B06 also still lacks a versioned PhysicsSpec/SceneSpec/BuildPlan path, active-camera visibility, and authentic independent human review.
