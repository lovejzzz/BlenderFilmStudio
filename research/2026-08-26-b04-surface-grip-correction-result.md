# B04 surface-grip correction — result

Date: 2026-08-26

Status: **FAIL**

## Result

The first correction preserved the compiler and motion, moved the prop-local grip by the preregistered `0.232 m`, and reproduced the scene in two clean builds.

- BuildPlan SHA-256: `7877e86642622330f1f2c786d132655558bfbbb153fa45cba831ed33efc2e025`
- Structure hash A/B: `cee99c325aa2a6973d99f7e68ec443b6241a2c7f9e7203c6f5975ba4a40bc717`
- Original contact checks: `10/10 PASS`
- HOLD surface overlap: `60/60 frames` — **FAIL**
- HOLD maximum inside-vertex depth proxy: `0.018445877 m` — **FAIL**
- Required exact separation: `0.001–0.003 m`; measured minimum: `0 m` — **FAIL**

## Falsified assumption

The declared shell distance assumed the visible hand box axes matched the semantic palm socket axes. The socket inherited the angled `hand.R` bone frame, while the hand proxy mesh coordinates were baked in actor/world rest space. Moving along socket-local Z therefore did not move along the visible hand's thin axis.

This is a coordinate-contract failure, not random render variation. The failed fixture and reports remain preserved under `experiments/contact-v0-2/`.

## Nonclaims

The result does not estimate force, pressure or penetration volume, and does not invalidate the compiler, parent switch or original 10 checks. It proves that those checks plus an unverified semantic frame were insufficient.
