# B18 Eevee sampling dose-response result

Executed: 2026-08-26 with real Blender 5.2.0 LTS build `fbe6228777e7` on Apple M4 Max.

Status: **NON_MONOTONIC_OR_UNSTABLE**

The protocol and six derived ReviewRenderSpec hashes were frozen in commit `86aaa1b` before the B18 runner or any B18 render existed. The runner was then frozen in commit `6d599ed`. Twelve clean Blender processes rendered 1,728 frames in the pre-registered interleaved order.

## Primary result

| Samples | Decoded exact | Exact cell | Failed pixels | Maximum error | Approx. 8-bit codes | PNG byte exact |
|---:|---:|:---:|---:|---:|---:|---:|
| 1 | 143/144 | no | 6 | 0.11764705181121826 | 30 | 0/144 |
| 2 | **144/144** | **yes** | **0** | **0** | **0** | 0/144 |
| 4 | 140/144 | no | 54 | 0.027450978755950928 | 7 | 0/144 |
| 8 | 137/144 | no | 76 | 0.0156862735748291 | 4 | 0/144 |
| 16 | 137/144 | no | 58 | 0.007843166589736938 | 2 | 0/144 |
| 32 | 133/144 | no | 67 | 0.003921598196029663 | 1 | 0/144 |

The exactness vector ordered `[1,2,4,8,16,32]` is `[false,true,false,false,false,false]`. Sample 1 did not replicate the strict exactness observed in B17, sample 2 happened to be exact, and every higher level was non-exact. The pre-registered decision is therefore `NON_MONOTONIC_OR_UNSTABLE`.

There is no supported simple threshold such as “one sample is deterministic” or “all levels below N are deterministic.” B17 remains a valid within-batch causal intervention, but B18 supplies a direct counterexample to generalizing its sample-1 result across fresh runs.

## New measured pattern

The maximum error ladder at samples 1, 4, 8, 16 and 32 is approximately 30, 7, 4, 2 and 1 eight-bit code values. Several higher-sample cells also disagree on the same frames or nearby coordinates: frames 9, 83, 91, 103, 104 and 144 recur across levels.

This pattern is **consistent with** rare stochastic sample contributions being averaged down as sample count increases. That is an inference from the measurements, not source-level proof of a particular Eevee random sequence, race or accumulation implementation. The exact sample-2 pair can be a lucky two-run observation; two runs per level cannot estimate its probability.

## Integrity

- all 12 runs observed source dither 1.0, set it to 0.0 in memory and never saved the source `.blend`;
- all six derived ReviewRenderSpecs matched their pre-registered SHA and differed semantically only at `proxy.renderSamples`;
- every run produced 144 exact filenames and retained camera/timeline identity;
- six OIIO reports bound all per-frame A/B hashes back to both sequence manifests;
- 13/13 negative cases reached the intended stable reason;
- source `.blend` SHA remained `2a505360…11b0b`.

## Next falsifiable boundary

The next experiment should increase replication depth rather than add more sample levels. A multi-run design at samples 1 and 2 can estimate how often a complete 144-frame sequence is pixel-exact and whether sample 2 is genuinely more reliable or was merely lucky. The preregistration must define the run count, all-pairs or reference-pair comparison graph, confidence interval and stopping rule before execution. In parallel, Blender/Eevee seed and evaluation controls should be enumerated from the real 5.2 RNA/API before selecting a scheduling intervention.

Artifacts:

- `experiments/eevee-sampling-dose-response-v0-1/results.json`
- `experiments/eevee-sampling-dose-response-v0-1/evidence/`
- `specs/eevee-sampling-dose-response-spec.v0.1.json`
- `research/2026-08-26-b18-eevee-sampling-dose-response-protocol.md`

