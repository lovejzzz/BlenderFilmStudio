# B11 appended-asset sanitization result

Date: 2026-08-26

Classification: **FIRST RUN FALSIFIED / SANITIZER PASS / FORMAL B11 TRUE**

## First-run falsification

A hash-valid, path-valid SET asset was generated from the clean B01 library and given four harmless but undeclared evaluation structures:

- one location driver;
- one object constraint;
- one rigid body;
- one two-key transform action.

The pre-remediation compiler appended the collection and successfully emitted a `.blend`. Therefore asset byte integrity did not imply asset behavioral integrity.

## Pinned-asset inventory

Nine assets referenced by B01–B08 were opened with auto-execute disabled and inventoried.

- seven contained no animation, drivers, constraints, rigid bodies, linked data or overrides;
- B03 and B04 character rigs each contained one named head rotation limit and two named gaze constraints targeting `GAZE_TARGET` inside the same collection;
- those six constraints are recorded as the narrow CHARACTER allowlist;
- zero forbidden findings remain in the pinned baseline.

The result is deliberately type-sensitive: SET and PROP assets remain pure data; CHARACTER assets may retain only the exact supported head/gaze rig constraints and internal armature modifiers.

## Post-append sanitizer

Immediately after append and before any compiler-authored behavior, Blender now inspects:

- object, object-data, material and node-tree animation/drivers;
- collection and shape-key animation/drivers;
- object constraints and pose-bone constraints;
- rigid bodies and rigid-body constraints;
- modifiers and their internal targets;
- linked objects, linked instance collections and external Blender libraries;
- library overrides;
- the Blender auto-execute setting and explicit `--enable-autoexec` flag.

## Evidence

Nine negative cases were rejected:

1. object driver;
2. shape-key driver;
3. object constraint;
4. rigid body;
5. pre-existing action;
6. linked external library;
7. linked-library override;
8. combined hidden-evaluation asset;
9. auto-execute enabled.

The B01 positive control remained accepted:

- plan SHA-256: `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`
- structure SHA-256: `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b`

B03 retained its published structure SHA-256 `96041c22a6626b4c5aceff3cc74155d5be411cfe0142f3025ecdf2d86d84d5ff`; B05 retained `a21c1e8944c50e528270cc314afbfe186a8d727ab5fb0dd0b4a8b078b4d315df`; B08 remained formal true with 132-frame zero-error replay and 8/8 trajectory negatives.

## Boundary

B11 detects declared Blender evaluation structures after the main asset file has been parsed. It does not yet provide a hardened file parser, OS process sandbox, memory/CPU quota, antivirus, signed asset package or complete Geometry Nodes/modifier semantic verifier.

The pre-registration mentioned a missing sanitizer report as a negative class. The implemented compiler deliberately accepts no external sanitizer report: it audits the live appended IDs itself, so there is no report artifact whose omission or substitution can bypass the gate. This is an architecture clarification, not counted among the nine executed attacks.

## Artifacts

- `research/2026-08-26-b11-asset-sanitization-protocol.md`
- `experiments/asset-security-v0-1/pinned-asset-inventory.json`
- `experiments/asset-security-v0-1/first-run-falsified.json`
- `experiments/asset-security-v0-1/results.json`
