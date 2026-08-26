# B10 restricted-path security result

Date: 2026-08-26

Classification: **FIRST RUN FALSIFIED / REMEDIATION PASS / FORMAL B10 TRUE**

## First-run falsification

The pre-registered harmless attack corpus found that the JavaScript BuildPlan compiler checked lexical paths but followed symbolic links during file reads. Six of eight negative cases escaped the intended boundary:

1. asset symlink to an external `.blend` copy;
2. SceneSpec symlink to an external JSON copy;
3. local provenance symlink to an external result copy;
4. TrajectorySpec symlink to an external trajectory copy;
5. render output directory symlink to an external directory;
6. BuildPlan CLI `--output` located outside the repository.

Each emitted a BuildPlan or wrote the plan outside the repository. Traditional lexical `..` traversal and `networkAccess: true` were already rejected by the SceneSpec schema.

No user secret or unrelated file was read. All external targets were harmless copies created inside a temporary experiment directory and removed after the run.

## Remediation

The compiler now:

- resolves the real repository root once;
- resolves every existing input to its real path before reading;
- requires both lexical and real paths to remain below the repository root;
- rejects any symbolic-link identity change, even when the link target would remain inside the repository;
- resolves the nearest existing ancestor of render and BuildPlan output paths before any write;
- applies the checks to SceneSpec, assets, ActorSpec, actions, GraspSpec, TrajectorySpec, source evaluation, local provenance, OutputSpec and OCIO configuration.

## Post-remediation evidence

- security negatives: 8/8 rejected;
- vulnerable cases remaining: 0;
- B08 positive BuildPlan SHA-256 unchanged: `7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9`;
- B08 full trajectory experiment: formal true, 8/8 trajectory negatives, 132-frame zero-error evaluation;
- B05 regression structural SHA-256 unchanged: `a21c1e8944c50e528270cc314afbfe186a8d727ab5fb0dd0b4a8b078b4d315df`.

## Boundary

B10 closes this specific local path and symbolic-link class. It does not yet prove OS-level sandboxing, protection from malicious Blender binary assets, denial-of-service resistance, package supply-chain integrity, authenticated approvals or a complete restricted tool gateway.

## Artifacts

- `research/2026-08-26-b10-path-security-protocol.md`
- `experiments/security-v0-1/first-run-falsified.json`
- `experiments/security-v0-1/results.json`
- `scripts/run-b10-path-security-experiment.mjs`
