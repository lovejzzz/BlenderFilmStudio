# B04 socket-frame correction — result

Date: 2026-08-26

Status: **GEOMETRY AUTOMATION PASS · PRESENTATION CAMERA ITERATED · HUMAN REVIEW PENDING**

## Reproducible correction

The second correction aligned `PALM_R` with the visible proxy frame before applying the frozen 2 mm contact shell. Asset binaries, Action, contact window, constraints, compiler and diagnostic thresholds were unchanged.

- ActorSpec SHA-256: `72f502846c14026f4be00e01ee148540c40fddb3721aebaf34842949fd4a7442`
- BuildPlan SHA-256: `31a00c586b04cb0156eaf0b2b5c2728e951f786e07cb883b601025a52c0d71a9`
- Clean structure hash A/B: `0359614194a9c476c99f85e92adc997c01e5c2079289e4ba41866ad4503f5c88`
- Geometry report A/B SHA-256: `2bca2750405b1de56dca5759ed5cd9e6f76e713275728794196e3d5131639087`
- Original checks: `10/10 PASS`; inherited negatives: `8/8 REJECTED`
- HOLD overlap: `0/60 frames`
- HOLD maximum inside-vertex depth proxy: `0 m`
- HOLD minimum exact unsigned surface separation: `0.001999974 m`
- Maximum socket position error: `1.6e-7 m`; rotation error: `0°`

## Camera visibility falsification

The first corrected clip candidate, `CLIP_C42N`, used the original presentation camera. Direct inspection suggested the head hid the contact pair, so a camera-visibility diagnostic was preregistered and run.

- Original camera: hand minimum/median visible fraction `0% / 0%`; prop `16.7% / 33.3%` — **FAIL**.
- At frame 78, all `12/12` hand triangle-centre rays first hit `HEAD`.
- `CLIP_C42N` SHA-256: `bcf9119413b7539135798958da958304b820d4208f74537de64a7145f14c1163`; it is retained as a rejected review candidate.

The independent rear technical camera used for `CLIP_D83K` passed the same visibility proxy:

- hand minimum/median visible fraction `25% / 66.7%`;
- prop minimum/median visible fraction `75% / 83.3%`;
- all samples remained in frame throughout HOLD.

`CLIP_D83K` is H.264, `960×540`, 24 fps, 144 frames, 6.0 seconds. SHA-256: `01467e0e946bb641211765ac7232e3968a16ee88768fc823c7329bbc265b5ebc`.

The generalized v0.2 aggregator was separately exercised with three schema-valid synthetic responses and one duplicate reviewer code: three were accepted, the duplicate was rejected, and the declared gates evaluated as expected. These synthetic documents are not committed, are not human evidence, and are not included in the zero-response status below.

## Current boundary

The rigid proxy now passes the declared geometric and visibility automation. This does not mean the motion reads as a credible pickup: the technical arm path travels near and behind the head, and the proxy has no fingers or force closure. Protocol v0.2 therefore keeps the human gate mandatory. With zero real responses, status is `PENDING_INSUFFICIENT_RESPONSES` and experiment completion remains false.
