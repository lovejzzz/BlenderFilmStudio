# B59-G0-R3-C4 · Spec-relative total-span attack correction

Date: 2026-08-29
Status: PREREGISTERED — implementation not yet changed
Formal R3 root at registration: absent

## Trigger and evidence

The C3 disposable rehearsal passed 14/14 pre-audit gates, its synthetic admissible control and every integrity check. It rejected 19/20 attacks. Only A06 was accepted because the attack hard-coded a 100-second forged total span; that is below the 360-second production minimum but above the shortened three-second rehearsal minimum.

- `results.json` SHA-256: `b25888e74bce21e4c095d617878c88c9eba95a223cc0f1cb1af8134805af9926`
- `audit.json` SHA-256: `125032e324d0dc7aed33bc279c34677dcecfa547b0398963e45eea4004bb5d3e`
- Rehearsal spec SHA-256: `4afde522c04e9a10ba747b04afbcff1d4f4aad5531043888b60214bf567102c1`
- Base formal spec SHA-256: `fd52dc1fe089a5cfe8eb099ae7ee01106a40b63428f01c7fe0a53fea60ec18f2`
- Tool commit: `41976982796ebf5507167bd0d2ab589934934cee`

The blocked rehearsal remains under `experiments/codex-host-stability-longitudinal-c3-rehearsal-v0-1` and grants no admission.

## Frozen correction

A06 sets the final sample capture time to exactly `minimumTotalSpanSeconds × 1000 - 1` milliseconds after the first sample. This guarantees a one-millisecond violation for every positive selected total-span threshold.

No production timing value, gate, observed parser, positive control or decision boundary changes. A fifth disposable rehearsal must pass 15/15 gates and 20/20 attacks before formal R3 may start.
