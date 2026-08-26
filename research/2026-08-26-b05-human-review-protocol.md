# B05 human review protocol v0.3

Status: locked before collecting any response.

## Asset

- clip ID: `CLIP_G52Q`
- file: `public/grasp-review/CLIP_G52Q.mp4`
- SHA-256: `f7f7c1ce3eaf36cacf8f3c5f4d143fbdcce574bfb61633b9bc9238cbc4f8cbaa`
- encoding: H.264 MP4, 960×540, 24 fps, 120 frames, 5.0 seconds
- review page: `/review-b05/`

The clip uses the authored B05 camera and final compiler 0.4.1 output. It contains no metric overlays, phase labels, pass/fail labels, or audio.

## Procedure

Each reviewer must watch the clip at normal speed at least twice before opening the machine-evidence page. The reviewer evaluates only visible technical motion: closure continuity, readability of two-sided contact, synchronized transport, visible mesh drift, and acquire/release position pops. The technical gripper must not be rated for anatomy, materials, acting, force closure, weight, or cinema quality.

The static page downloads a local JSON response and transmits nothing. Reviewer codes must be anonymous. Responses are accepted only when they validate against `specs/human-review-response.v0.3.schema.json`, match the exact clip hash, and use a unique reviewer code.

## Frozen aggregate gates

At least three authentic independent valid responses are required. PASS additionally requires:

- median closure continuity at least 4/5;
- median two-sided contact readability at least 4/5;
- median synchronized transport at least 4/5;
- zero `YES` responses for visible mesh drift;
- zero `YES` responses for visible position pop;
- strict majority `PASS` overall and zero `FAIL` overall.

`UNSURE` is not silently converted into a pass. Invalid or duplicate responses are reported but excluded. No synthetic, model-authored, copied, or researcher-invented response is permitted.

## Decision boundary

Passing this rubric would support only the claim that the compiled technical motion is visually readable to this small pilot group. It would not establish population preference, physical grasp stability, realism, anatomy, acting, or film-production acceptance.
