# RC6 FLIP particle detail attempt-37 result

Status: **RETAINED AUDIT-HARNESS FAILURE (26/27)**

The one permitted zero-bake Blender process completed successfully and reproduced the prior aggregate particle counts exactly. The independent audit passed 26 of 27 checks. Its only failed check was `activeOutlierDetailsRecomputed`: 16 of 36 repeated observations differed by exactly `0.00000001 m` when the auditor recomputed one-voxel penetration from the already rounded eight-decimal local coordinate. The scene-side value was computed from the unrounded coordinate and then rounded once. This is an auditor numeric-provenance error, not a scene or physics discrepancy. The attempt is retained without overwrite or Blender rerun.

## Measured physical finding

- Frames 1-3: zero active FLIP particles outside the one-voxel cup-interior envelope.
- Frames 4-7: the same nine active particles remain outside only the floor envelope, producing 36 repeated observations.
- All nine are `ALIVE`, have reported RNA speed `0.0`, and lie in `INSIDE_CUP_SOLID_FLOOR`.
- Their cup-local Z range is `-0.18023688 m` to `-0.17396487 m`; the modeled inner floor is `-0.16 m` and the modeled outer bottom is `-0.22 m`.
- Interior-floor penetration is `13.96487-20.23688 mm`. None is below the modeled outer bottom, outside the outer radius, or above the rim.
- The nine unique local positions remain byte-identical across frames 4-7 while display indices change. The evidence therefore describes a small retained particle cluster embedded in the collider's solid floor, not an actively moving leak through the complete cup.

The previously measured surface amplification remains material: nine active outlier particles at frame 7 corresponded to 7,814 below-floor reconstructed mesh vertices. Collision correction must precede surface reconstruction tuning, and any correction should be tested in the product's Preview/Review tiers before one Final confirmation.

## Binding

- Execution receipt hash: `5c32c481138382fef4864ec539436f8c090bfdf2f2a4f5675fd25054ffac11b2`
- Result hash: `e3e52359bfc4d2191b162384b9b5890e547416defc1ead4c0fdd025f708f3794`
- Result file SHA-256: `93b4a12a9e797463635b5b98a247fabbeffd9b74b602dd90ccfb8144538fd569`
- Failed audit hash: `7667372e092c968930ac5a32385e72a335ec13682c1df3a2299a97bceb7fcf60`
- Failed audit file SHA-256: `0161a3695f4dfca8f5512b4c08be56ab86dc1dcda41f9bec060444f3be1f0e41`

Next correction: add a versioned, audit-only C1 verifier that accepts at most half of the last reported decimal place (`0.000000005 m`) plus floating arithmetic slack when checking derived penetrations. It must retain exact hashes for every reported detail and all other 26 checks, and it must not rerun Blender or mutate attempt-37.
