# RC6 C20 C4 — retained historical-view reconstruction failure

Date: 2026-09-02
Status: retained audit-only harness failure; physical verdict unchanged

C4 corrected the generated Python audit namespace and independently replayed
the centroid distance from the published eight-decimal samples. The measured
delta is `1.0177317821824516e-8 m`, below the preregistered `2e-8 m` bound, so
`metricsRecomputed` now passes. Every one of the 27 physical booleans also
recomputes exactly. The retained C20 scientific verdict remains `FAIL 23/27`.

The audit finished at `23/25`. Its two failures are historical-view errors in
the audit-only adapter, not physical or evidence mutations:

1. Expected retained process argv used the fresh C4 audit root where the real
   attempt-94 Blender argv correctly names the retained attempt-94 evidence
   root.
2. The original pre-audit manifest was captured before `independent-audit.json`
   and its stdout/stderr logs existed. Replaying that historical snapshot over
   the completed root must exclude those later three outputs in addition to the
   manifest itself.

Attempt-97 contains only `admission.json`, `audit.json` and this failure record.
It started no Blender process and performed no Bullet or liquid bake, render,
save, build, network call, engine write or retained-root write. Keep it
immutable.

The next gate is audit-only C5. It may make exactly the two historical-view
corrections above, preserve C4's shared execution environment, and use a fresh
attempt-98 root. All replay tolerances, physical checks, retained data and
hashes, claim ceiling and zero-Blender resource limits remain frozen. Do not
render or test another particle radius.
