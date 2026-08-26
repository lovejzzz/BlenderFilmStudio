# B19 Fast GI × TAA reprojection factorial protocol

Date frozen: 2026-08-26, before implementing the B19 configurator/runner and before rendering any B19 frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Evidence-supported candidates

B18 rejected a simple sample-count threshold. Its non-exact maximum errors generally shrank with sample count, and several frame/coordinate neighborhoods recurred. A real Blender 5.2 RNA inventory of the exact B02 scene then found:

- Fast GI enabled, with 2 GI rays and 8 steps;
- TAA temporal reprojection enabled;
- ray tracing, bokeh jitter and the only light's shadow jitter disabled;
- no explicit render seed exposed in the queried RNA.

This does not prove Fast GI or reprojection is causal. It justifies testing the two enabled sampling/evaluation subsystems before guessing at hidden scheduling state.

## Frozen design

The machine contract is `specs/eevee-gi-reprojection-factorial-spec.v0.1.json`.

At fixed 32 Eevee samples and output dither 0, render a full 2×2 factorial:

| Cell | Fast GI | TAA reprojection | Clean runs |
|---|:---:|:---:|---|
| G1-R1 | on | on | A, B |
| G0-R1 | off | on | A, B |
| G1-R0 | on | off | A, B |
| G0-R0 | off | off | A, B |

All eight runs cover frames 1–144 in the frozen interleaved order. A single B19 configurator must verify source dither=1, Fast GI=true and reprojection=true, then set dither=0 plus both requested factor states in memory. It must report before/requested/after and never save the source `.blend`.

The B14 renderer, B15 comparator, 32-sample ReviewRenderSpec, receipt, `.blend`, Blender binary and OCIO remain byte-frozen.

## Exact gate and decisions

Within each cell, A/B is exact only with 144/144 decoded frames, max error 0 and zero failed pixels. The overall exactness pattern maps to one frozen label:

- `FAST_GI_CAUSAL_SUPPORT`: both G0 cells exact, both G1 cells non-exact;
- `REPROJECTION_CAUSAL_SUPPORT`: both R0 cells exact, both R1 cells non-exact;
- `JOINT_DISABLE_SUPPORT`: only G0-R0 exact;
- `EITHER_DISABLE_SUPPORT`: only G1-R1 non-exact;
- `NO_SUFFICIENT_INTERVENTION`: all four non-exact;
- `BASELINE_UNSTABLE_OR_MIXED`: baseline exact or any other valid pattern;
- `INVALID_EXPERIMENT`: a control or attack fails.

No post-hoc tolerance or nearest-story relabeling is allowed.

## Controls and attacks

Every run binds exact input/tool/config bytes; verifies observed factor values and 32 samples; preserves camera/timeline state; produces exactly 144 named, hashed frames in distinct A/B directories; and records a self-hashed sequence manifest. Each OIIO comparison binds both sequence hashes and all per-frame A/B hashes.

At least 14 negative cases cover five identities, fixed dither, both factor observations, sample count, alias directories, missing/extra/mutated frames and comparison binding.

## Non-claims

An exact disabled cell locates a causal control under this profile but does not identify an internal race or make the disabled look acceptable. Two runs per cell do not estimate reliability. Nothing extends to Cycles, EXR, another machine or another Blender version.

