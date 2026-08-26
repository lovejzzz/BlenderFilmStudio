# B04 corrected contact — blinded human review protocol v0.2

Date: 2026-08-26

Status: frozen before clip rendering and response collection

Candidate: `CLIP_D83K`

## Purpose

Test whether independent viewers find the corrected rigid-proxy pickup visually readable after automated geometry and camera-visibility gates pass.

`CLIP_A17F` is the frozen centre-grip baseline. `CLIP_C42N` is a rejected camera candidate because the head occludes the contact pair. Neither is pooled with this protocol.

## Locked review asset

- Source: clean build A of `B04.socket-frame.scene.json`.
- Frames: `1–144` at `24 fps` (`6.0 s`).
- Geometry, motion, constraints and timing: unchanged from the socket-frame correction.
- Review camera: `(0, 4.6, 1.85) m`, looking at `(-0.05, 0.02, 1.42) m`, 58 mm lens.
- A camera-aligned area light may expose the technical proxy; it may not change silhouettes, geometry or motion.
- Output: H.264 MP4, `960×540`, no audio, no labels or metrics burned into the image.
- The final byte SHA-256 is recorded after rendering; rerenders are new assets and may not reuse `CLIP_D83K`.

The chosen presentation camera passed the preregistered triangle-centre visibility diagnostic for both `HAND_R` and `PROP_BODY`. Reviewers are not shown that result before responding.

## Blinding and collection

1. Reviewers open only `/review-b04-v02/` before submission.
2. They watch the clip at normal speed at least twice and do not inspect frame-by-frame metrics first.
3. The static page downloads a local JSON response. It transmits nothing and requests no name or email.
4. Reviewer codes must be unique, anonymous, and 3–24 characters.
5. Responses are validated against `human-review-response.v0.2.schema.json`; invalid and duplicate-code responses are rejected with reasons.
6. A minimum of three valid independent reviewers is required.

## Questions and gates

The form freezes the same seven items as protocol v0.1: approach naturalness, support readability, distracting intersection, visible pop, weight coherence, overall acceptance and an optional note.

The aggregate passes only when all are true:

- valid reviewers `≥ 3`;
- approach, support and weight medians each `≥ 3/5`;
- fewer than half answer `YES` to distracting intersection;
- fewer than half answer `YES` to visible pop;
- a strict majority answer overall `PASS`.

## Stopping rule

No result is reported before three valid responses. All valid responses received before the first aggregate are included. If the gate fails, the result remains a failure; the clip, thresholds or questions are not edited post hoc.

## Nonclaims

This pilot is not population-level preference research. A pass would not establish fingers, force closure, pressure, friction, anatomy, weight simulation, acting or cinematic quality. A failure would not invalidate the compiler or geometry measurements.
