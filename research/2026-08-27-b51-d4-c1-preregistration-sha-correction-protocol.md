# B51-D4-C1 · preregistration SHA literal correction

Status: preregistered before correction tooling or experimental output.

## Retained failure

The first frozen D4 tool stopped before creating its output root. Its ancestor gate used the nonexistent full commit literal `8494459f1f18a00de9e0fb3dfb9aaf01e93b49cb`; the repository resolves the already-published preregistration commit to `8494459950d3b822e3641d14e7608bf046f305f7`. Git rejected the invalid name, and the runner then failed closed with `B51-D4 preregistration is not an ancestor`.

The retained failure is `experiments/native-split-backend-assembly-derivation-preflight-failure-v0-1/failure.json`, SHA-256 `4f39426853bb9d27de0d45eaa1cd69c43a249a1c38b816e40fb04e3554ab2635`. It records zero Blender processes, zero renders, zero EXRs read or written, no output-root creation and no scientific observation.

## Frozen correction

C1 may change exactly one value in the assembly runner:

- `PREREGISTRATION_COMMIT`: replace the nonexistent literal with `8494459950d3b822e3641d14e7608bf046f305f7`.

No spec, input identity, pass routing, metadata contract, admission threshold, output count, attack, verdict, audit rule or non-claim may change. Both corrected scripts must be committed and pushed before execution. The corrected run must use a new receipt bound to that corrected tool commit. Any further failure is retained and requires a separate correction.

## Interpretation boundary

This correction repairs provenance admission only. It does not make the failed attempt valid and cannot support an EXR assembly, determinism, image-equivalence, rendering or backend claim.
