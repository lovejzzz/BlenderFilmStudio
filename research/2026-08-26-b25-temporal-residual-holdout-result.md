# B25 temporal residual holdout result

Date executed: 2026-08-26

Decision: **`STATIC_ONLY_ENVELOPE_FAIL`**

Experiment validity: **true** (`19/19` frozen negative cases passed)

Human review: **PENDING**

## What actually ran

The frozen order A → B → C produced three independent Blender render processes (PIDs `84684`, `86173`, `87449`). Each rendered frames 1-144 sequentially in one process. Total output was 432 newly rendered PNG8 frames, with no derivation image reused.

The three pair comparisons produced 432 static frame observations and 429 adjacent-frame residual transitions. Source `.blend`, plan, structure, Blender, OCIO, ReviewRenderSpec, controls and all tool/file bindings passed exact gates.

## Frozen-gate outcome

Temporal residual envelope:

- `429/429` transitions passed;
- `354/429` were strictly exact;
- worst maximum absolute residual delta: `0.003921598196029663` (approximately one PNG8 code value);
- worst RMS residual delta: `0.000015081015555200999`;
- worst changed spatial pixels: `17`.

Static B24 PNG8 envelope:

- `430/432` frame pairs passed;
- `394/432` were strictly exact;
- worst maximum absolute error: `0.003921598196029663`;
- worst RMS error: `0.000013060542585672345`;
- worst changed spatial pixels: `17`.

The frozen static spatial ceiling was `16`, so two observations failed by one pixel. The max and RMS ceilings still passed.

## Failure localization

Both failures are frame 38:

- A-B: 17 changed pixels;
- A-C: 17 changed pixels;
- B-C: frame 38 is decoded-pixel exact.

The A-B and A-C changed-pixel coordinate sets are identical: one 17-pixel cluster spanning image rows 112-117 and columns 267-272. This supports an A-associated one-frame render event; it does not identify the lower-level GPU cause.

Because the pre-registered gate requires all 432 static observations to pass, the result cannot be promoted to temporal support even though all temporal transitions passed. The static threshold is not widened after observation.

## Interpretation boundary

This result supports the narrower statement that the newly held-out sequences stayed inside the derived temporal residual envelope. It simultaneously falsifies the broader production gate formed by combining that envelope with the B24 static spatial ceiling.

It does not prove invisible flicker, smooth cinematic motion or final-delivery quality. The review proxy is 960×540 PNG8, motion blur is disabled, and no calibrated viewer has completed the blind-review protocol.

## Next falsifiable step

Preserve this failure, prepare a randomized human-review package without using automation as a surrogate reviewer, and separately investigate why a same-process continuous sequence can produce an isolated A-only 17-pixel cluster when B and C agree exactly at that frame.
