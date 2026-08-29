# B59-G0-R3-D1-C2 · Colima quoted-field correction

Date: 2026-08-29
Status: PREREGISTERED
Formal D1 root: absent

The C1 rehearsal passed 10/10 attacks and all live integrity checks. Its samples correctly recorded `running: true` and four expected containers, but the log-envelope quote was included in `arch: "aarch64\""` and `runtime: "docker\""`. Result and audit SHA-256 are `dc866d29a1776be5ce229819a0a170ff73e12f399541a40b62f3b97fa9fdf7eb` and `4ecb76d93a99334d5b06a9a342abb059e834bd48a3f3e529b5033c70167661c5`.

C2 changes only both parsers from an unrestricted non-space token to a token excluding whitespace and `"`. The failed rehearsal is retained at `experiments/codex-host-disk-attribution-c1-rehearsal-v0-1`. A new rehearsal must pass 8/8 and 10/10 before formal execution.
