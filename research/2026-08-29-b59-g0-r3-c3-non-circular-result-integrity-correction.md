# B59-G0-R3-C3 · Non-circular final-result integrity correction

Date: 2026-08-29
Status: IMPLEMENTED — synthetic control validated; A06 fixture blocked by separately preregistered C4
Formal R3 root at registration: absent

## Trigger

The C2 disposable rehearsal again passed 14/14 pre-audit gates, 20/20 attacks and all 12 live/file integrity checks, yet the independent auditor blocked its synthetic admissible control.

- Rehearsal `results.json` SHA-256: `7d2d70ca3cf50e602f0eb40c47a42ab903af51c9df94aae3b869ed64edd95cb6`
- Rehearsal `audit.json` SHA-256: `d0362300c88463834178f31a72bd7862f6b22b7226db333fc70c9a2b24463789`
- Rehearsal spec SHA-256: `05f9f314d1e0b60055022873a4d20ca74b8e6bf0d9079d59bcd1fed13cc42435`
- Base formal spec SHA-256: `accaac000fa879486d2cced9bfda65d8968dd3a377ad391504c428dc99ccf31d`
- Tool commit: `56ad31b20eb279a2bc38a1fa5aa4b142df87aca1`

The failed rehearsal is retained under `experiments/codex-host-stability-longitudinal-c2-rehearsal-v0-1` and is not admission evidence.

## Root cause

The result includes both its gate vector and its self-hash. Asking `EVIDENCE_BOUNDED_AND_SELF_HASHED` inside that vector to prove the final result hash creates a circular statement: setting the gate changes the content covered by the hash, and updating the hash changes whether the previously projected gate was evaluated against current content. No ordering of a finite number of seals makes this self-referential proof well-founded.

The runner never used final-result self-validity to project this gate; it projected bounded, self-hashed start/sample evidence, then sealed the final result. The auditor had added the circular condition and therefore did not mirror the producer contract.

## Frozen correction

`EVIDENCE_BOUNDED_AND_SELF_HASHED` continues to require:

- exact start receipt hash, self-hash and byte ceiling;
- exact ordered sample hashes, self-hashes and byte ceilings;
- declared result byte count no larger than the frozen result ceiling.

Final-result self-hash validity remains mandatory in two non-circular places: the independent `SELF_HASHES` file-integrity check and `validateCandidate` after gate projection. A candidate with an invalid result self-hash remains rejected. A20 continues to push declared result size above the ceiling and must be rejected.

No observed gate, resource threshold, timing rule, mutation input or decision boundary changes. A fourth disposable rehearsal must pass 15/15 gates, 20/20 attacks, the synthetic positive control and all integrity checks before formal R3 may start.
