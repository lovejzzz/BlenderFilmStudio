# B40-R1 · Post-intervention re-admission replay failure

Runner verdict: `WORKER_HOST_CAPACITY_READMISSION_FAILED`  
Independent audit: `FAIL`  
Runtime operations: `0`

## What passed

The frozen runner measured an accepted decision at every unchanged B40 capacity gate:

- host available: `139038380032` bytes; `117563543552` bytes after the frozen 20 GiB projection, above the 100 GiB reserve;
- VM memory: `12513595392` bytes, above 10 GiB;
- VM CPUs: `6`, above five;
- Docker filesystem available: `14767869952` bytes, above 8 GiB;
- VM swap: zero;
- `qemu-x86_64`: enabled, `/usr/bin/qemu-x86_64`, flags `POCF`;
- running containers: zero.

The in-process analyzer passed and all 16 preregistered mutation attacks produced their expected primary rejection code.

## Why the result is rejected

The runner's final pre-persistence comparison reported `replay=FAIL`. It therefore correctly changed the hashed `replayPassed` field to `false` and emitted the failure verdict. The independent audit then rejected the receipt at `REPLAY_RESULT_RECORDED`; it did not reinterpret the accepted capacity decision as an accepted experiment.

The original runner did not persist which replay component differed. A post-hoc diagnostic constructed from the persisted observations can reproduce equal analysis and attack vectors after restoring `replayPassed=true`, but that does not recover the original transient mismatch and is not accepted evidence.

## Required correction

B40-R2 must be separately preregistered. It may change only replay diagnostics and comparison order: snapshot the evidence before any attack evaluation, compare canonical serialized projections, and persist component-level equality booleans inside the evidence before hashing. Capacity policy, probes, expected accepted gates, 16 attacks and the zero-runtime boundary remain frozen.

Artifacts: `experiments/worker-host-capacity-readmission-v0-1/attempt-1-results.json` and `attempt-1-audit.json`.
