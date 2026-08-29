# B62-Q1-D6-C3 · Correct the measured 32-bit EXR output budget

Date: 2026-08-29  
Status: PREREGISTERED — v0.1 through v0.3 retained; no C3 tool change exists yet

## Failure classification

D6 v0.3 crossed the Blender 5.2 ACES 2.0 setup and began the sealed roster. The budget guard terminated the render process after 27.074 seconds when the evidence root reached 141,074,598 bytes, exceeding the frozen 134,217,728-byte ceiling. The receipt records `BUDGET_EXCEEDED`, `OUTPUT_BYTES`, no Blender crash, no RSS breach and no wall-time breach.

Eleven multilayer EXRs and ten PNGs were written before termination. Those partial images are invalidated and must not be opened or used to tune the retry. C3 is a resource-accounting correction only.

## Measured projection

The eleven EXRs total 133,786,016 bytes; the largest is 12,168,649 bytes. Sixteen at that measured maximum project to 194,698,384 bytes. The ten PNGs total 6,708,248 bytes, projecting to roughly 10.7 MB for sixteen. Adding the fresh scene, process receipts, render report, independent report, audit and receipt remains well below 256 MiB.

C3 therefore replaces the base 128 MiB `projectedWriteBytes` and child `maxOutputBytes` with 268,435,456 bytes. This is a bounded, evidence-derived correction, not an unbounded allowance. The 107,374,182,400-byte minimum free reserve remains unchanged; the host had roughly 283 GiB free after v0.3.

## Authorized implementation

Only the Node runner and auditor may change. They must bind C3 and the immutable v0.3 tree, use fresh v0.4, and enforce the replacement byte ceiling in admission and every child receipt. All three Blender Python tools remain byte-identical to commit `7622c31636e4016998862c9d5f34c6fc7d4c010c`.

No camera, frame, color, render, geometry, pixel, process-count, threshold or verdict field may change. v0.4 must rebuild the scene and rerender all sixteen images; it may not resume or reuse v0.3 outputs.
