# RC2 physical-light transfer — accepted-binary development pass

Date: 2026-09-01
Verdict: `DEVELOPMENT_PASS_FORMAL_BUILD_BLOCKED`

RC2 transfers the physical-film method from the retained robot holdout to a
smaller unseen mechanism. A grooved ceramic sphere rolls under Blender gravity,
contacts a Bullet-owned hinged shutter, opens the physical light path and comes
to rest behind the gate. A passive collision stop, not a pose key, owns the
stable final shutter angle. The reveal lamp remains at exactly 1050 W with zero
animation channels; the measured illumination change comes from evaluated
occluder geometry.

The accepted development evidence root is
`experiments/physical-light-transfer/RC2-2026-09-01-development-attempt-02`.
Its root-manifest hash is
`811a5b843005937605c0a10157049f5cdb5137af5c5818897a3c7f5c11b88497`.
Attempt-01 is retained as a sealing-harness failure: the first sealer rejected
the valid nonzero exit used by the blocked host preflight.

## Measured result

- Frozen machine acceptance: 19/19 `PASS`.
- Direct still-and-clip review: 9/9 `YES`.
- Contact and first shutter response: frame 51; delay 0 frames.
- Actor travel: 4.1908872 m.
- Median rolling slip ratio: `1.48e-6`.
- Peak shutter opening: 98.80388412°; settled window starts at frame 76.
- Actor and shutter pose-key authority: 0 / 0.
- Reveal-light animation channels: 0; power remains exactly 1050 W.
- Actual/open receiver luminance divided by closed counterfactual: 2.663735624.
- Reopened maximum actor-location delta: `3.725290298461914e-9` m.
- Reopened maximum shutter-angle delta: `4.300723333017231e-9`°.
- Workspace inspect/execute route, three negative controls and exact RC1 result
  hash regression all pass.

The reusable product increment remains two paths and 652 additions / 5
deletions on branch `codex/rc2-physical-light-transfer`. It contains no frozen
fixture identity and is not committed or published. The validated local
`physical-film-direction` skill now records metric visible/collision/measurement
congruence, hinge sweep and passive-stop checks, and static-light closed-occluder
counterfactuals.

## Claim ceiling and next gate

This result proves accepted-binary development of one reusable rolling-body,
hinged-occluder and static-light path on the admitted M2 Max. It does not prove
the preregistered clean native build, a distributable product binary,
photorealistic asset quality or cross-platform behavior.

The read-only host screen currently reports 130 GiB free against its
conservative 160 GiB clean-build threshold. No formal native build may start
until exact safe cleanup targets totaling at least 30 GiB are specifically
confirmed, removed without touching retained evidence, and the preflight
passes.
