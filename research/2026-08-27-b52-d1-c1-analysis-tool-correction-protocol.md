# B52-D1-C1 · analysis-tool correction protocol

Status: frozen after the first B52-D1 analysis attempt failed and before any corrected result was produced.

## Observed failure

All 30 preregistered Blender 5.2 CPU processes completed successfully, with 30 EXRs and 30 worker reports. The frozen analyzer then reached attack A16 and called no-argument `dict.pop()`. Python requires a key, so analysis stopped before `results.json` was written.

The exact failure and original run-receipt identity are retained at `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/analysis.failure.json`. The render receipt remains byte-unchanged.

## Permitted correction

Only the A16 mutation changes: delete the registered `BFS_MASTER.Normal` dictionary key explicitly. The quality equations, semantic decoder, thresholds, matrix, selection rule, render artifacts and timing observations do not change.

The corrected analysis must:

1. reuse the original 30-render receipt without rerendering;
2. bind runner and renderer to the original tool-freeze commit;
3. bind analyzer and audit to a new correction tool-freeze commit;
4. include the failure evidence and original receipt hashes in the result;
5. pass all 20 attacks;
6. reproduce the corrected result byte-for-byte in an independent audit.

If any condition fails, B52-D1 remains invalid rather than receiving a quality–cost verdict.
