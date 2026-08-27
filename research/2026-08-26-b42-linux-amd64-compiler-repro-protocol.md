# B42 · Linux/amd64 compiler reproducibility protocol

## Falsifiable question

Can the exact Blender 5.2 Linux/amd64 worker already identified by B41-D3 compile the B01 still life and B02 dolly scene twice from independently regenerated immutable BuildPlans, reproduce their frozen semantic structure hashes, and reject a BuildPlan whose declared hash was altered?

## Why this is the third gate

B41-D3 established that this image can execute Blender and complete a Cycles CPU render. B42 removes rendering from the workload and tests the actual studio boundary: `SceneSpec → BuildPlan → Blender scene`. Passing means that a subscription-driven coding agent can author deterministic structured inputs and delegate scene construction to a free Blender worker. It does not mean the resulting film is already photoreal or production complete.

## Frozen design

- The exact image ID, Blender Linux executable SHA-256, source specifications, assets, compiler, schema, OutputSpec, and OCIO configuration are pinned in `specs/linux-amd64-compiler-repro.v0.1.json`.
- B01 and B02 each regenerate the BuildPlan twice. Both serialized plans must match the previously frozen plan file SHA-256 and internal `planHash`.
- Four separate containers start with four empty output directories: B01-A, B01-B, B02-A, B02-B.
- Each container has no network, no capabilities, no privilege escalation, a read-only root and repository mount, and one nested writable output mount. The hard memory, CPU, PID, shared-memory and wall-time bounds are frozen.
- Acceptance compares `scene.structure.canonical.json` byte-for-byte within each benchmark and checks its SHA-256 against the frozen structure hash. `.blend` hashes are recorded but not required to match.
- One fifth container receives B01 with only the top-level `planHash` replaced by 64 zeroes. It must fail nonzero and emit `BuildPlan hash mismatch`.

## Failure rule

Any identity drift, plan-generation drift, compile timeout/error, manifest-binding mismatch, structure mismatch, missing tamper rejection, unexpected build/pull/download, residual experiment container, or independent-audit failure rejects the B42 verdict. Partial evidence remains evidence; no failed run may be silently overwritten.

## Explicit non-claims

B42 does not render pixels, prove visual quality, prove Eevee/GPU availability, prove `.blend` byte identity, cover arbitrary scenes, or provide remote attestation.
