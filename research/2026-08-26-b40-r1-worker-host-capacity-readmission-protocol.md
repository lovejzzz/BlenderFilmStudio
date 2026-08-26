# B40-R1 · Worker host capacity re-admission protocol

Status: preregistered after an authorized external-state intervention and before experiment tooling or output.

## Why a new experiment

B40-C5 is an immutable receipt of a blocked host. It cannot be rerun or reinterpreted after cleanup. The user then explicitly authorized removal of re-downloadable caches, deletion of LTX model data, and a Colima resize. B40-R1 asks whether the changed host now satisfies the exact same policy.

This is not blinded. Manual checks already indicated that the intervention probably succeeded. Those checks are context, not accepted evidence: B40-R1 must independently probe, persist, replay and audit the state with a frozen toolchain.

## Frozen boundary

- Reuse the B40 worker ceilings and capacity policy without weakening any value.
- Read only host statfs, Colima status/config, VM meminfo/CPU/Docker filesystem/binfmt, Docker running-container IDs, and pinned ancestry hashes.
- Execute no Colima mutation, container lifecycle operation, download or Blender process.
- Require all seven capacity gates to be `ACCEPTED`, no blocked reason, zero runtime operations, stable JSON replay and all 16 adversarial checks.

## Interpretation

The strongest accepted verdict is `WORKER_HOST_CAPACITY_ACCEPTED_REPLAY_STABLE`. It means only that the host is eligible for a separately preregistered B41 runtime canary. It does not claim that Blender 5.2 works under linux/amd64 emulation or that any render is correct.
