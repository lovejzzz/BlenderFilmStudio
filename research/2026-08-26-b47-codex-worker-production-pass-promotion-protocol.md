# B47 — B44 `.blend` to reproducible multipart production passes

Date: 2026-08-26

Status: preregistered before formal renderer, runner or audit

## Purpose

B46 established exact ordered Combined pixels and temporal deltas for two bounded intervals. A film workflow also needs scene-linear depth, normals, motion vectors and stable object mattes. B47 asks whether those production representations survive the same semantic-build boundary, rather than assuming that a valid Combined image implies valid compositing passes.

## Derivation boundary

B47-D1 was a one-file exploratory probe frozen before execution. It discovered exactly seven float subimages, a finite `1e10` Depth background sentinel, non-zero Vector data for the moving camera with motion blur disabled, and a parseable Object Cryptomatte manifest. D1 did not compare builds and cannot pass B47. Its committed output fixes the formal layout and pass-specific rules without using formal holdout results.

## Formal design

The formal inputs remain the four B44 `.blend` files. Each runs once in a fresh pinned Blender 5.2 Linux/amd64 container and renders two ordered frames: TABLETOP 21–22 and INTERIOR 9–10. Render settings remain the B46 128×72, eight-sample Cycles CPU control. Motion blur and denoising remain off so representation reproducibility is not confounded with a quality intervention.

Every Render Result is saved once as RGBA32 ZIP `OPEN_EXR_MULTILAYER`. Blender's bundled OpenImageIO decodes all eight files and canonicalizes all seven subimages independently. The cross-build decision therefore contains 28 exact pass pairs: two scenes × two frames × seven passes.

The pass roster is Combined, Depth, Normal, Vector and CryptoObject00–02 with the exact D1 channel layout. All components must be finite. Combined and Normal must contain non-zero content; Depth must be positive and at most the observed `1e10` far sentinel; Normal must remain inside [-1,1]. Each TABLETOP Vector must contain non-zero finite values. Cryptomatte must declare the frozen hash/conversion/layer name, parse as JSON, contain every frozen asset mesh name and match exactly across A/B within a shot.

The moving TABLETOP control requires Combined, Depth, Normal and Vector hashes to change between frames 21 and 22 in both builds. The static INTERIOR control requires all seven pass hashes to remain unchanged between frames 9 and 10 in both builds. These are machine-domain semantics, not a perceptual motion-quality claim.

## Execution boundary

The experiment permits exactly one image inspection, four isolated Docker runs, eight successful frame renders, eight host EXR analyses and one final running-container check. It forbids build, pull, download, review encoding and model/Codex/video API calls. The common disk guard retains 100 GiB after a frozen 1 GiB projected write. A wrong declared source SHA stops before any container.

## Promotion rule

B47 passes only if all four workers and eight multipart outputs complete, all layouts and pass semantics hold, all 28 cross-build pass pairs are exact, both temporal controls hold, all 18 attacks reject for their frozen reason, the evidence self-hash matches and an independent audit reopens every EXR and recomputes the decision.

Passing would establish a bounded reproducible production-pass handoff. It would not establish visual quality, motion blur, denoising, 4K, downstream compositing quality, complete shots or throughput. Those interventions belong to B48 after the representation itself is verified.
