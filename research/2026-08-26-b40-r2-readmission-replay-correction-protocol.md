# B40-R2 · Re-admission replay correction protocol

Status: preregistered before correction tooling or output.

B40-R1 measured all capacity gates accepted and detected all 16 attacks, but its aggregate pre-persistence replay comparison failed without retaining the differing component. B40-R2 is a narrow correction. It freezes every scientific and capacity condition from R1 and changes only evidence snapshotting, comparison order and diagnostic persistence.

The tool must JSON-snapshot the tested evidence before analysis, record separate evidence/analysis/attack equality booleans inside the evidence before self-hashing, and derive `replayPassed` from their conjunction. Any later mismatch must flip the corresponding stored field, recompute the evidence hash and reject. The independent audit must reproduce all three replay components and the exact recorded attack vector.

The strongest accepted verdict remains `WORKER_HOST_CAPACITY_ACCEPTED_REPLAY_STABLE`. Passing only admits a separately preregistered B41 runtime canary.
