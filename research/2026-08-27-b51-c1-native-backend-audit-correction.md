# B51-C1 · Native backend independent-audit correction

Date: 2026-08-27

Status before correction: `ANALYSIS PASS · INDEPENDENT AUDIT EXCEPTION`

B51-D1 completed all eight frozen Blender processes and its analyzer returned `NATIVE_CYCLES_BACKEND_DERIVATION_USABLE` with 14/14 mutation attacks. The first independent-audit invocation then raised `AttributeError: 'str' object has no attribute 'open'` while hashing the audit script itself. No audit artifact was created.

C1 freezes a narrow correction. It may:

1. normalize the audit helper input through `Path(path)`;
2. verify each qemu parent EXR byte hash directly against the preregistration;
3. reproduce the legacy B49 Combined canonical hash, whose metadata header uses `"name":"Combined"` rather than the B51 fully qualified subimage name;
4. verify every tool recorded in the original receipt against the exact Git blob at the original tool-freeze commit;
5. replay the unchanged analyzer and require byte-exact equality with the unchanged `results.json`.

C1 may not rerender, rewrite the run receipt, rewrite the result, change any metric, relax any gate or discard the initial exception. The failure is retained as `experiments/native-cycles-backend-derivation-v0-1/audit.initial-failure.json`.
