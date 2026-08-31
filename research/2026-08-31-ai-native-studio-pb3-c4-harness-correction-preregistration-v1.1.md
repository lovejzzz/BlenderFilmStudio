# PB.3 C4 harness correction preregistration v1.1

Date: 2026-08-31

Status: `PREREGISTERED_INERT_TOOLING_NOT_IMPLEMENTED_EXECUTION_UNAUTHORIZED`

## Purpose

C3 attempt-02 is a retained failure even though all four authorized semantic
Blender processes completed successfully. This preregistration freezes two
harness corrections before any tool implementation:

1. normalize the single `--tool-contract` option to its resolved absolute path
   before C3 authority validation or process creation; and
2. set `bpy.context.preferences.filepaths.file_preview_type` to `NONE` and
   assert it immediately before saving the editable workspace.

The machine contract is
`specs/ai-native-studio-pb3-validation-c4-harness-correction.v1.1.json`,
SHA-256 `194d3e9d1be415d29646f59ded6be94371e18db13a383d7a48d57a44aa741ece`.

## Frozen interpretation

The first change resolves a spelling mismatch created by the wrapper itself:
the recorded processes used a relative tool path while the verifier resolved
the same argument. It does not change which tool bytes are executed.

The second change prevents Blender from creating save-preview PNGs. It does not
exclude, reclassify or delete the two PNGs observed in attempt-02, and it does
not weaken the frozen base auditor. A future run must still contain no EXR,
PNG, JPG, JPEG, MOV or MP4 file anywhere in the complete work root.

All B01/B02 canonical, semantic, provenance, workspace, Expert-state, resource,
process-count, log and zero-render/network/engine-write conditions remain
unchanged. The versioned helper may differ from its frozen parent only by the
preview-type assignment/assertion before save. The versioned runner may add
only the path normalization plus C4 authority/retained-root bindings.

## Current boundary

Attempt-01 and attempt-02 remain immutable. The future attempt-03 work and
evidence roots do not exist. This preregistration authorizes no Blender start,
proposal execution, BuildPlan write, scene change, render, network call,
`film-engine` mutation or PB.4–PB.7 work.

The next action is an inert versioned tool freeze with self-tests, exact diff
checks and negative controls. Only after that freeze passes may an exact
attempt-03 authorization request be issued.
