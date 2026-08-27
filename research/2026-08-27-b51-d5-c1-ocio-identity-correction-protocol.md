# B51-D5-C1 · OCIO identity path correction

Status: preregistered after the retained preflight failure and before correction tooling or render output.

## Retained failure

The first D5 frozen runner stopped at parent/source admission before creating its output root or launching Blender. Five parent artifacts, two source `.blend` files and both H1 CPU EXRs matched. The D5 spec instead named a nonexistent OCIO path, `blender/ocio/aces_2.0/config.ocio`, with an unrelated hash.

The immutable failure is `experiments/native-cpu-data-pass-sample-cost-preflight-failure-v0-1/failure.json`, SHA-256 `b094e07a87d112d21d8ee4217bfb04572729bc6433b50e7f384bb43c36d154bd`. It records zero Blender processes, zero renders, zero EXRs written and no scientific observation.

## Only allowed correction

C1 may change exactly the D5 spec's two OCIO identity fields to the already-bound H1 values:

- URI: `color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio`
- SHA-256: `24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`

The runner's frozen D5 spec SHA constant must then bind the corrected spec. No source, variant, operation, sample, repeat, seed, render profile, threshold, attack, capacity limit, decision rule, output root, operation boundary or non-claim may change. Corrected tools must be committed and pushed before retry.

This repair aligns D5 with its exact H1 parent and the OCIO identity already embedded in both `.blend` bindings. It does not make the failed attempt valid and cannot support a data-pass or cost claim.
