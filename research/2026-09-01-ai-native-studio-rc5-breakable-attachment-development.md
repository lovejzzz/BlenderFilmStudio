# RC5 development result — physical secondary event

## Result

RC5 development is `PASS_DEVELOPMENT_ACCEPTED`; the later formal clean-build
attempt is also accepted. Exact commit `8e18c825…` is now public on
`lovejzzz/film-engine/main`.

The accepted candidate is product commit
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900`, whose only changed path is
`scripts/modules/film_studio_physics_action.py`. The accepted evidence root is
`experiments/physical-richness/RC5-2026-09-01-development-attempt-13`.

## What the software learned

- A breakable attachment target is selected from the released initiator's
  metric ray with a unique closest-member margin; no observed bottle index is
  typed after the solve.
- A native Blender Bullet fixed constraint owns cap detachment. The input may
  define the physical threshold, but it may not define a break frame, detached
  pose or detachment velocity.
- A detached secondary body is measured separately from the named bottle-group
  settle predicate.
- Molded household glass uses bounded 0.45 mm two-lobe contact ovality on the
  visible collision-source mesh. This prevents ideal-cylinder rolling without
  pose keys, damping tricks or solver sleep.
- Contact/effect camera choice uses a bounded projected-separation search and a
  single reused camera object, preserving the baked rigid-body cache.

## Measured result

- Build checks: 20/20 `PASS`.
- Basketball/bottle contact: frame 16.
- Cap detachment: frame 24; maximum attachment separation 0.12205441 m.
- Bottle response: 3/3; settled group window frames 132–141.
- Reopen checks: 7/7, maximum transform deltas below `1e-8`.
- Exact regressions: RC4, D1 and H1 all `PASS`.
- Authority negatives: 12/12 reject.
- Review artifacts: three 1280×720 stills and one fixed-camera 48-frame clip.
- Direct visual review: 10/10 `YES` across all 48 frames.
- Independent audit: 27/27 `PASS`, audit self hash
  `b7020a9b00b53565d18bb4e8a222881470defbb7f022912e994aeaa20ca37adf`.

## Retained scientific failures

Attempts 01–10 preserve target-selection, inspection, settle, serialization,
regression-isolation and factory-world failures. Attempt-11 proves that a
machine-complete solve can still fail direct visual review when the cap is
camera-occluded. Attempt-12 proves that creating/deleting temporary candidate
cameras can invalidate Blender's rigid-body cache. Attempt-13 corrects only
those learned causes without weakening physical, authority, resource, reopen,
regression or visual thresholds.

## Claim ceiling and next action

This proves one Blender Bullet basketball/three-bottle scene with a
solver-broken cap attachment, non-ideal bottle contact and derived
secondary-event cinematography on the accepted M2 Max host. It does not prove
fracture mechanics, deformation, liquid slosh, sound, arbitrary scene quality,
cross-platform support, production readiness, signing, notarization or public
distribution.

## Formal result

Formal attempt-01 is accepted. One local-only clone and clean native arm64
build produced binary SHA-256
`ad08b54132b75325a12580f705fdefc205dd4444a36f2491e4d8a200e1091ef2`.
Four offline product starts reproduced exact result hash `6bc858c6…`, 20/20 B1
checks, 7/7 reopen, RC4/D1/H1 regressions, 12/12 negative controls, three stills
and 48 clip frames. Fresh formal direct review passed 10/10.

The base independent audit is retained at 26/27 `FAIL`: it searched the full
source/build workspace for media and therefore counted 3,829 immutable Blender
source fixtures and application resources as scene render leakage. Frozen C1
changed only that scope to the formal scene `runtime`, found zero leaked media,
and passed 10/10. Its audit self hash is
`bca9164656f30757ad646aa2c629230c051c923edc2df375ed7377ea73f533f0`.
No source, build, Blender, physics, render, visual, threshold or resource action
was rerun for C1.

Formal evidence is
`experiments/physical-richness/RC5-2026-09-01-attempt-01`. One ordinary
fast-forward published exact commit `8e18c825…` from public parent `db662438…`.
Git ref, GitHub API, tree OID and raw source hash agree; no tag, Release, LFS or
binary was uploaded. Publication evidence is
`experiments/physical-richness/RC5-publication-2026-09-01-attempt-01`.
