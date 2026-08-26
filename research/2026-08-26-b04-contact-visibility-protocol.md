# B04 contact visibility diagnostic — preregistered protocol

Date: 2026-08-26

Status: frozen before execution

Input: compiled `B04.socket-frame.scene.json`, unchanged geometry and motion; presentation camera only

## Question

Does the review camera show enough of both `HAND_R` and `PROP_BODY` during the 60-frame HOLD window for a human to judge their relationship?

The geometry correction can pass while the camera hides the interaction behind the head or body. This diagnostic is a presentation gate, not a collision or realism metric.

## Locked method

1. Reproduce the review camera at `(2.45, -4.30, 1.85) m`, looking at `(-0.05, 0.02, 1.30) m` with a 62 mm lens.
2. At every HOLD frame (`49–108`), evaluate Blender's dependency graph.
3. Explicitly tessellate the evaluated `HAND_R` and `PROP_BODY` meshes with `Mesh.calc_loop_triangles()`.
4. Use each evaluated triangle centre as a deterministic surface sample.
5. Project each sample into the active camera. A sample is *in frame* only when normalized X and Y are in `[0,1]` and depth is positive.
6. Cast a ray from the camera to every in-frame sample. A sample is *visible* only when the first hit object is the sampled object.
7. Report per-object and per-frame in-frame and visible fractions plus the first-hit occluder counts.

## Preregistered gates

For **both** `HAND_R` and `PROP_BODY`:

- at least `50%` of tessellated surface samples are in frame at every HOLD frame;
- at least `25%` of all tessellated surface samples are directly visible at every HOLD frame;
- median directly visible fraction across HOLD is at least `35%`.

These intentionally low thresholds reject grossly hidden evidence; they do not establish good composition.

## Interpretation

- Passing permits creation of a blinded review candidate; it does not pass human review.
- Failing invalidates the clip as evidence of visible contact, but does not invalidate the underlying geometry result.
- Camera changes may be explored only in a new, separately hashed review candidate. Geometry, motion, constraints and compiler evidence remain frozen.

## Nonclaims

The diagnostic does not measure attention, silhouette quality, focal hierarchy, editing, acting, weight, anatomy or cinematic composition. Triangle-centre sampling is a deterministic proxy, not a perceptual visibility model.
