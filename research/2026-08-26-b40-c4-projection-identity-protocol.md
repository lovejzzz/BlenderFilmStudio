# B40-C4 · Projection identity source correction

Status: `PREREGISTERED_IDENTITY_SOURCE_CORRECTION_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26  
Parent: B40-C3 `NO_RESULT_TOOL_CRASH`

C3 attempted to obtain the B40-C2 experiment's own identity from a nonexistent nested field in the C2 spec. B40-C4 changes only that source:

- old: `c2Spec.serializationCorrection.*`;
- new: frozen library constants `B40_C2_PREREG_COMMIT` and `B40_C2_SPEC_SHA256`.

The projected evidence remains schema `bfs.workerHostCapacityEvidence.v0.3`, experiment `B40-C2`. C3 ordered failure-code projection, C2 serialization stability, C1 flags parsing, all capacity policy and observations, 14 attacks and zero-runtime boundary remain unchanged.

The strongest accepted verdict remains `WORKER_HOST_CAPACITY_BLOCKED_REPLAY_STABLE`. A pass proves a replay-stable blocked admission receipt, not B41 eligibility.
