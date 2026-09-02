# RC6 C26 C1 — retained pre-root log-path harness failure

Date: 2026-09-02
Status: retained execution failure before attempt-105 root creation

The frozen C1 audit-only adapter at execution commit
`53d1b54d` was started once with system Python. It verified its generated source
before execution, then stopped while loading the retained process logs. The
adapter had changed the process receipt to
`01-real-impact-water-diffusion.json` but left two inherited C18 paths:

- `logs/01-real-impact-fractions-threshold.stdout.log`
- `logs/01-real-impact-fractions-threshold.stderr.log`

Those files do not exist in immutable C26 attempt-104. The correct retained
names are `01-real-impact-water-diffusion.stdout.log` and
`01-real-impact-water-diffusion.stderr.log`.

The exception occurred before `FRESH_EVIDENCE.mkdir`. Attempt-105 remains
absent. Counts are one system-Python start and zero evidence-root creation,
Blender, Bullet, Data, Mesh, render, save, network or retained-root writes.
C26's physical `FAIL 23/27` and original audit `19/20` remain unchanged.

A versioned C2 may change exactly those two generated log-path literals and use
fresh attempt-106. It must retain the C1 adapter and absent attempt-105 state,
preserve the one-comma normalization and every physical/evidence check, and
remain audit-only.
