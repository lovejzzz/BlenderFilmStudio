# B59-G0-R3-C2 · Synthetic-control sealing-order correction

Date: 2026-08-29
Status: PREREGISTERED — implementation not yet changed
Formal R3 root at registration: absent

## Trigger

The C1 disposable rehearsal produced valid actual intervals (`1,036`, `1,033`, `1,031` ms), passed 14/14 pre-audit gates and rejected 20/20 registered attacks. The independent auditor nevertheless returned `BLOCKED_HOST_STABILITY` because its synthetic admissible control reported `valid: false`. All 12 file-integrity and live-replay checks were true.

- Rehearsal `results.json` SHA-256: `8a7210868c2e89fb7ee5b3f553ceae1e39144af11bac956c49b84be505d2da9d`
- Rehearsal `audit.json` SHA-256: `18a330a1daba6dc912ce784592a0f587c6849ad58a6e57a63021ccb128a4566b`
- Rehearsal spec SHA-256: `b2b2af5e27aaeb339de50fabca0cce54eafce82a516b15601e20d0f4315ee5f6`
- Base formal spec SHA-256: `d5d7c3d6cab4bcf03e569cfa5fb45e7a3bea3b6b3a54bdaded0476319dd8771a`
- Tool commit: `1c9a0de8b1aa5d5e06edef79a92d4fc9a42b02b4`

The failed rehearsal is retained under `experiments/codex-host-stability-longitudinal-c1-rehearsal-v0-1` and is not admission evidence.

## Root cause

`resealBundle` updated start/sample hashes and result receipt references, then projected gates. During projection, `expectedGates` correctly checked the result self-hash, but that hash still represented the pre-update result. It therefore projected `EVIDENCE_BOUNDED_AND_SELF_HASHED: false`. A final result seal made the hash valid but did not recompute the already projected gate. The validator correctly rejected this internally inconsistent positive control.

## Frozen correction

After updating receipt references and before projecting gates, seal the result once. Then project gates, failures and verdict, and perform the existing final seal. This creates a valid input hash for the evidence gate and then binds the projected fields.

No formal evidence parser, observed gate, threshold, attack mutation, file integrity check or decision boundary changes. A third disposable rehearsal must pass 15/15 gates, 20/20 attacks and every integrity check before formal R3 may start.
