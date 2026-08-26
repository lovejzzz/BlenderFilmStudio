# B24 production-repeatability envelope holdout protocol

Date frozen: 2026-08-26, after derivation and before implementing the B24 comparator or runner or rendering any B24 holdout frame.

Status: **PRE-REGISTERED / NOT EXECUTED**

## Question

Does the numeric repeatability envelope derived from B21/B23 generalize to 24 algorithmically selected, previously unused timeline frames while provenance and structure remain exact?

The machine contract is `specs/production-tolerance-holdout-spec.v0.1.json`. The derivation artifact is `experiments/production-tolerance-derivation-v0-1/results.json` and is explicitly labeled derivation-only.

## Frozen holdout

The rule is every frame from 1 through 144 where `frame mod 6 = 4`. This yields:

`[4, 10, 16, 22, 28, 34, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94, 100, 106, 112, 118, 124, 130, 136, 142]`.

None overlaps the twelve B20-B23 sentinels. The set and order are frozen before any B24 render.

Each frame receives A/B/C fresh-process replicates. Every process renders once and saves the same Render Result as display PNG8 and scene-linear EXR32, producing 72 processes, 72 render calls, 144 saves and 72 replicate-pair comparisons per format.

## Frozen envelope

EXR32 per pair:

- maximum absolute error ≤ `0.0078125`;
- RMS error ≤ `0.0000152587890625`;
- zero-threshold failed pixels ≤ `512`.

PNG8 per pair:

- maximum absolute error ≤ `0.003922`;
- RMS error ≤ `0.0000152587890625`;
- zero-threshold failed pixels ≤ `16`;
- OIIO Yee failure pixels = `0` at 100 cd/m² and 45°.

Every pair must pass every applicable ceiling. Aggregate means cannot hide a failing pair, and thresholds cannot be widened after execution.

## Frozen decisions

- both formats 72/72 → `PRODUCTION_REPEATABILITY_ENVELOPE_SUPPORT`;
- EXR fails, PNG passes → `SCENE_LINEAR_ENVELOPE_FAIL_DISPLAY_PASS`;
- both fail → `DISPLAY_AND_SCENE_LINEAR_ENVELOPE_FAIL`;
- EXR passes, PNG fails → `DISPLAY_ONLY_ENVELOPE_FAIL`;
- any control failure → `INVALID_EXPERIMENT`.

## Critical boundary

This is a numeric repeatability validation, not a calibrated human-visibility or cinema-quality study. OpenEXR and PNG are evaluated separately because scene-linear and display-referred errors are not interchangeable. The Yee auxiliary metric uses recorded nominal viewing inputs and cannot replace temporal playback or human blind review.

## Controls and attacks

Source `.blend`, ReviewRenderSpec, Blender, OCIO, B23, derivation artifact and the reused B22 configurator/B21 renderer are frozen by hash. Twenty-two negative categories cover identities, controls, holdout/run order, 72 unique processes, one-render/two-save scope, both layouts, files, comparison binding, envelope mutation and Yee parameter mutation.

## Freeze statement

At this commit, `blender/compare_b24_holdout_tolerance.py` and `scripts/run-b24-production-tolerance-holdout.mjs` do not exist. No B24 holdout output has been rendered.
