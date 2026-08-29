# B62-Q1-D4 · Native-resolution paired human review

Date: 2026-08-29  
Formal evidence: `experiments/b62-camera-quality-holdout-render-v0-5`  
Machine status: technical `PASS`; scientific `B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT`  
Human review status: COMPLETE — DIRECTIONALLY IMPROVED, NOT PROMOTABLE

## Method and boundary

All twelve 960×540 review PNGs were opened at native resolution after the formal receipt existed: six frames in timeline order, with ORIGINAL and CORRECTED both inspected. A two-column contact sheet was used only to inspect progression; each image was also opened individually. The labels were known, so this is an engineering review, not a blinded preference experiment.

The review does not alter the frozen geometry result, convert 16-spp diagnostics into final-quality claims, or establish general cinematic merit.

## Pair observations

| Frame | ORIGINAL | CORRECTED | Human disposition |
|---:|---|---|---|
| 193 | Helmet surface fills almost the entire frame; character action and environment are unreadable. | Upper body, illuminated visor/eye region, raised arm and chamber lights are simultaneously readable; useful negative space remains. | Clear improvement; composition usable as a diagnostic close shot. |
| 204 | Same extreme occlusion; only blurred surface lighting is legible. | Character silhouette and environment remain separated; action is still readable. | Clear improvement. |
| 228 | Extreme occlusion persists. | Profile, eye/visor, chest and shoulder hierarchy remain readable. | Clear improvement; slightly tighter but still balanced. |
| 252 | Frame is effectively an abstract helmet surface. | Character remains identifiable, but head and shoulder scale now dominate more of the frame. | Improvement, with emerging temporal framing pressure. |
| 276 | No usable subject or environment relationship. | Face anchors remain visible, but background context and body articulation are substantially reduced. | Improvement, but too tight for stable promotion. |
| 288 | No usable composition. | Character is readable, yet helmet and shoulder crowd the frame and leave little breathing room. | Reject for promotion; agrees directionally with the frozen 0.933787 area failure. |

## Conclusion

The bounded D3 transform fixes the catastrophic original occlusion, but it is not a valid full-shot camera solution. It applies one fixed azimuth/radial/lens correction across a moving source camera; as the shot evolves, apparent subject scale grows monotonically and the corrected composition drifts from a readable close shot into an over-tight crop.

The evidence therefore supports a narrower design statement: the failure is correctable, but the correction must be motion-aware across the shot rather than a single static transform. The next experiment must preserve the current 0.90 limit and test a bounded temporal camera path or scale compensation. It must not promote the v0.5 camera, exclude frame 288, or reinterpret this non-blind review as preference evidence.

## Evidence identities

- Root: 35 files, 54,124,627 bytes, tree SHA-256 `f1f25fa48d1ab4ad54970ae0e599e8cd66c7684d1b5677fc3053b7a894d5dec7`
- Receipt file SHA-256 / self-hash: `8a7c6cd045eaf9d180cc332bb909fc73efc518703b8cd60e5f09d066ab4bbe64` / `119c1028e2a3e079af6ca0497cd3da3ac60a4ac690d984d77f377b8087e1d73b`
- Audit file SHA-256 / self-hash: `97fcca32776027335c9c104d4c5995af28cf17cc241a042c5f2e154f0a442cd9` / `e832532c2046dede02403d3546c3a46978b6aa509a7416d970a330888f058b87`
