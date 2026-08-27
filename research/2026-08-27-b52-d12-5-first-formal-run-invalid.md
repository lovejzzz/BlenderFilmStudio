# B52-D12.5 first formal run — invalid infrastructure failure

Date: 2026-08-27

Status: `INVALID_NO_SCIENTIFIC_VERDICT`

The single-use D12.5 root was created and retained. Twelve real Blender 5.2 Cycles renders, six adapters, twelve paired-radius consumers and twenty-four typed-envelope encoders completed successfully in 54 unique child processes. The 55th unique child, the independent analyzer, exited 1 before writing `results.json`.

The failure was a result-serialization bug. One computed subset flag remained a NumPy `bool_`; Python's standard JSON encoder rejected it while constructing the evidence hash with `allow_nan=False`. The error occurred after analysis but before any result document was written. No measurement, threshold outcome or fixture pixel value was inspected during diagnosis. Only the traceback, execution counts and absence of `results.json` were read.

This run has no scientific verdict and cannot be resumed or reused. D12.5-C2 may change only the explicit cast of that subset flag to built-in `bool`, update experiment/root identities and rerun the unchanged matrix from a fresh root after a new frozen preflight. Fixtures, radii, numeric gates, coverage gates, decision rules and attack contract remain unchanged.

Evidence:

- failed root: `experiments/blender-static-radius-intervention-holdout-v0-1/`;
- `run.failure.json` SHA-256: `e90d0e26d936e35c6882a04863d2bd1e406b65db3899ca77df58a904c02ebc61`;
- `execution.json` SHA-256: `81c311ac7586ba3c72edc129eabb276b04e7bec3bcd730b6f72949171bc01880`;
- execution internal hash: `54ede7909f581aee0c81cbfde47b5ebeafad48212d1112cb595dc1abb2493d98`;
- analyzer stderr SHA-256: `3a1d504a3bbdc45268cdb269f7d40a83645425b7009416d17fd7d76a5b042403`;
- `results.json`: absent.
