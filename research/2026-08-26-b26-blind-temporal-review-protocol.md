# B26 blinded temporal review protocol

Date frozen: 2026-08-26, after an exploratory carrier test and before implementing the formal package generator or collecting any review response.

Status: **PRE-REGISTERED / NO HUMAN RESULT**

## Why automation stops here

B25 passed 429/429 temporal residual transitions but failed two of 432 static observations. Neither fact answers whether a person sees flicker or a stability difference during playback. B26 therefore separates carrier integrity, interface pilot and formal independent observation.

The current ITU-R BT.500-15 recommendation states that, unless a selected method says otherwise, at least 15 observers should be used. A smaller exploratory study must be labeled informal. It also distinguishes expert/non-expert observers and says observers should not have been directly involved enough in development to acquire specific detailed knowledge of the system.

Reference: <https://www.itu.int/rec/R-REC-BT.500-15-202305-I/en>

## Carrier gate

Ordinary H.264 delivery would introduce a lossy encoding confound. Every A/B/C source sequence must instead be independently encoded as lossless VP9 Profile 1, `gbrp`, 960×540, 24 fps, six seconds and no audio with the frozen FFmpeg 8.1.2 binary.

Each carrier is decoded back to 144 RGB frames. Acceptance requires 144/144 exact decoded RGB frames, zero maximum error and zero changed pixels. Dropping alpha is allowed only if all source alpha samples are verified as exactly 1.0.

The pre-freeze exploratory A carrier met that RGB roundtrip condition, but it is not a formal B26 artifact and cannot be promoted.

## Observers and balancing

The formal target is 18 valid independent observers: the six A/B/C permutations appear exactly three times. The formal minimum is 15, but 15-17 remains `FORMAL_REVIEW_INCOMPLETE` until the balanced target is reached.

The project owner/developer may run an `INTERFACE_PILOT_ONLY` session. That response cannot enter the formal sample. Any independent sample smaller than 15 is `INFORMAL_REVIEW_ONLY`.

## Primary session

Observers see only `CLIP-01`, `CLIP-02`, `CLIP-03`. The A/B/C mapping is salted and committed by SHA-256, then sealed outside the observer package until responses lock.

Each clip plays twice at 1× in its assigned order, without pause, seek or loop controls. The observer records a five-level temporal-instability rating, confidence and optional time/location. Three pairwise comparisons allow left-more-stable, indistinguishable or right-more-stable. Optional diagnostic replay begins only after primary responses lock and is reported separately.

## Viewing record

Every formal response binds anonymous observer ID, expertise, development involvement, acuity/colour screening, display model/resolution/refresh/scaling/brightness, player/browser, OS, distance, ambient light, timestamps, schedule commitment and carrier hashes.

## Conservative formal outcomes

- all 18 observers rate all clips NONE/BARELY_VISIBLE and all pairs INDISTINGUISHABLE → `NO_DIFFERENCE_OBSERVED_UNDER_TEST_CONDITIONS`;
- at least two independent observers locate the same MILD-or-worse clip/time region, or the same directional pair preference with overlapping location/time → `VISIBLE_TEMPORAL_DIFFERENCE_SUPPORT`;
- target complete but neither rule met → `OBSERVER_DISAGREEMENT`;
- any identity, carrier, schedule, blinding, response-lock or viewing-record failure → `INVALID_REVIEW`.

The no-difference label is deliberately conditional. It is not proof of invisibility or general cinematic quality.

## Freeze statement

At this commit, `scripts/run-b26-blind-temporal-review-package.mjs` does not exist. No accepted carrier, schedule, observer interface or human response exists.
