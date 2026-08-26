# B10 restricted-path security protocol

Status: pre-registered before the first adversarial run.

## Question

Can an otherwise valid SceneSpec or compiler CLI request make the JavaScript BuildPlan stage read from or prepare writes outside the repository by placing a symbolic link below an allowed path?

The test uses only harmless temporary files created by the experiment. It does not target user secrets or unrelated data.

## Threat model

The current schema rejects lexical `..`, absolute asset paths, network asset URIs, `networkAccess: true` and `arbitraryPython: true`. The suspected gap is time-of-check/path-identity disagreement:

- the JavaScript compiler checks normalized path strings;
- Node file reads follow symbolic links;
- Blender later resolves real paths, but an external read may already have occurred;
- output roots and the BuildPlan CLI output may also have a symlinked ancestor.

## Frozen cases

1. allowed asset URI whose final file is a symlink to a harmless external `.blend` copy;
2. SceneSpec input path below the repository that is a symlink to an external JSON copy;
3. local provenance URI symlinked to an external copy;
4. TrajectorySpec URI symlinked to an external copy;
5. render output root whose existing directory is a symlink to an external directory;
6. `--output` BuildPlan path explicitly outside the repository;
7. lexical asset `..` traversal;
8. SceneSpec requesting network access;
9. unchanged B08 positive control.

Cases 1–8 must be rejected before external data is read or a BuildPlan is written. Case 9 must still emit the same plan hash.

## Remediation requirement

Every existing input path must be resolved to its real path before reading. Both the lexical and real path must remain below the real repository root, and any symbolic-link path identity change is rejected. For output paths, the nearest existing ancestor receives the same real-path check before any write or Blender execution.

## Regression boundary

The patch must preserve:

- B08 BuildPlan SHA-256 `7a4bccb640130db2dbf5c315907f81d5462605b6939b00a9df672c362d544dd9`;
- B05 structural SHA-256 `a21c1e8944c50e528270cc314afbfe186a8d727ab5fb0dd0b4a8b078b4d315df`;
- B08 132-frame zero-error evaluation and 8/8 trajectory negatives.
