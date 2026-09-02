# RC6 C20 attempt-93 — retained restart interruption

Date: 2026-09-02
Status: interrupted for an owner-requested Codex restart; no scientific verdict

The frozen C20 experiment started from commit
`a1dfc659b4bb9ba639e1f57ff31a9062a7ba38cf`. It changes only simulation
particle radius `1.8 → 1.6` on the C18 baseline. About two minutes after launch,
the owner asked to restart Codex. The foreground runner received `SIGINT` and
exited 130. A process check then found no remaining runner, `caffeinate` or
Blender process.

The retained workspace contains the exact source copy, 11 configuration files
and 11 partial Data VDB files: 23 files and 3,579,112 bytes total. Data did not
complete, Mesh never started, and no render, `.blend` save, build, network call
or engine write occurred. Only `admission.json` existed in the evidence root
before this interruption record was written. There is no result, receipt or
independent audit and therefore no physical PASS/FAIL inference.

Attempt-93 is immutable and must never be resumed or repaired. After restart,
run the normal host preflight, then freeze a versioned C20 C1 restart adapter.
That adapter may change only the fresh work/evidence roots to attempt-94; it must
preserve particle radius1.6, every other C18 input, all27 checks and all resource
ceilings. Commit the adapter while attempt-94 roots are absent, then run once
under `caffeinate`. No render is allowed before a completed physical pass.
