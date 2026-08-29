# B58-E1-C4 · Nested production-preflight correction

Date: 2026-08-29
Status: PREREGISTERED AFTER ZERO-BLENDER REHEARSAL FAILURE, BEFORE OFFICIAL OUTPUT

## Counterexample

Fresh-clone rehearsal at tool-freeze commit `8f8a07d41c8237575011d1480baff0e45fa5289b` passed the C3 direct-entry production preflight when its preflight root had one component below `experiments/`. The exact B58 call instead used `<b58-preflight-root>/production-preflights/BASELINE_B01`. Its child exited before producing a receipt with `ENOENT` while creating that nested root. The outer preflight then attempted to read the absent receipt and reported a second `ENOENT`, obscuring the child failure.

The direct child and outer stderr line SHA-256 values are `590727f67f0260937d4684669ac2925d8bab7d3b05eb958758deaf94c1c0dfb2` and `91ba680702818d9f56c03b317fbf4af1eb522e5e5898a6d4011fde2762c2dc58`. Both failures occurred with zero Blender, render, model, network or Docker processes. All three official B58 roots remain absent.

## Frozen correction

The B58 caller must durably create exactly `<b58-preflight-root>/production-preflights` after its existing release, Gate 0, path, disk and root-freshness checks and before spawning the first child. Each B57 production preflight remains responsible for exclusively creating its own final case directory; no B57 byte changes are authorized.

After a child returns, B58 must check the exit code and receipt existence before reading JSON. A failed child stops the sequence and surfaces a bounded diagnostic containing case id, exit state, stdout and stderr. It must never be reclassified as an accepted preflight and must not spawn later children. Two C4 attacks independently remove parent preparation and bypass child-failure propagation.

C4 changes no SceneSpec, BuildPlan, production compiler, receipt verifier, disk threshold, process ceiling, DAG, restart decision, formal gate denominator or verdict threshold. It only makes the already preregistered nested case layout executable and preserves the actual failure reason.
