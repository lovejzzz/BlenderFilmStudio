# B14 receipt-bound review dailies protocol

Date frozen: 2026-08-26, before implementing the sequence renderer, packager or verifier and before rendering the formal 144-frame sequence.

Status: **PRE-REGISTERED / NOT YET EXECUTED**

## Observed gap

B13 proves that an immutable BuildPlan can produce a receipt-bound `.blend` with reproducible semantic structure. PixelSpec v0.1 proves exact same-machine decoded pixels for four selected 4K Cycles frames. Neither experiment proves that one receipt-bound shot can traverse every timeline frame, produce an exact gap-free sequence and become a playable video whose frames remain auditable.

A full B02 master at the measured 4K/512-sample CPU rate would take roughly 12–15 serial hours for 144 frames. That is a real cost observation, not permission to relabel a cheaper render as a master. B14 therefore tests a separately typed review-proxy layer.

## Question

Can the exact B02-A compile receipt drive real Blender 5.2 through all frames 1–144, producing a complete 960×540 Eevee PNG sequence and a 6-second H.264 review file, while preserving source scene identity and making every frame, tool and container independently verifiable?

## Frozen render profile

The authoritative machine-readable contract is `specs/review-render-spec.v0.1.json`.

- source: exact B02-A receipt file, receipt body hash, execution identity, BuildPlan hash, structure hash and `.blend` SHA-256;
- Blender: exact 5.2.0 LTS binary and build `fbe6228777e7`;
- OCIO: pinned ACES 2 CG config;
- frames: 1–144 inclusive at 24/1 fps;
- image sequence: 960×540, 8-bit RGBA PNG;
- renderer: Blender Eevee, 32 render samples, motion blur off;
- review transform: `sRGB - Display` / `ACES 2.0 - SDR 100 nits (Rec.709)`;
- video: external FFmpeg 8.1.2, H.264/libx264, CRF 18, medium preset, yuv420p, no audio, fast-start, stripped metadata and bitexact flags.

The profile is intentionally lower cost and lower quality than the published 3840×2160, 512-sample Cycles PixelSpec. Every artifact and page must display `REVIEW_PROXY_NOT_MASTER`.

## Frozen positive gate

1. B13 verifier passes the exact source receipt before Blender starts.
2. Receipt file SHA, receipt body hash, execution identity, BuildPlan hash, structure hash, source `.blend` SHA, Blender binary SHA, FFmpeg binary SHA, ffprobe binary SHA and OCIO SHA match the frozen spec.
3. Blender validates the embedded scene plan/structure/manifest markers before rendering.
4. Blender records camera identity, frame range, fps and camera animation key data before proxy overrides; those identity fields remain invariant after rendering.
5. Exactly 144 files named `frame-0001.png` through `frame-0144.png` exist, with no missing or extra PNG frame.
6. Every frame has a byte count and SHA-256 entry. A canonical sequence-manifest body has a self-hash.
7. FFmpeg consumes the numbered PNG sequence and emits one MP4. The exact command and tool identity are recorded.
8. ffprobe reports H.264, yuv420p, 960×540, 24/1 fps, exactly 144 decoded frames, 6 seconds and no audio stream.
9. A video SHA-256 and evidence-package manifest bind the source receipt, render spec, renderer source, sequence manifest, encoder command and MP4.
10. Frames 1, 72 and 144 are published as visual witnesses, with the complete MP4 available for human review.

Formal B14 automation is true only if every positive requirement and all 10 frozen attacks pass. Human/cinematic acceptance remains separately pending.

## Frozen negative matrix

Attacks operate only on copied receipts/specs/evidence and disposable outputs:

1. `N_RECEIPT_FILE_SHA`: mutate the frozen receipt-file SHA in a copied spec;
2. `N_RECEIPT_BODY_HASH`: mutate the frozen internal receipt hash in a copied spec;
3. `N_BLEND_SHA`: mutate the source `.blend` SHA in a copied spec;
4. `N_PLAN_MARKER`: mutate the expected plan hash in a copied spec;
5. `N_MISSING_FRAME`: remove one copied frame from an otherwise valid evidence package;
6. `N_EXTRA_FRAME`: add `frame-0145.png` to a copied package;
7. `N_FRAME_SHA`: mutate one copied PNG byte while retaining the old manifest;
8. `N_SEQUENCE_SELF_HASH`: alter the sequence manifest without updating its self-hash;
9. `N_VIDEO_SHA`: mutate copied MP4 bytes while retaining the old evidence manifest;
10. `N_VIDEO_PROBE`: substitute or declare probe properties that violate frame count, dimensions or rate.

Each attack must fail with its intended stable reason, not merely malformed JSON. No authoritative receipt, source `.blend`, tool binary or formal evidence will be modified.

## Evidence retention

Tracked evidence will contain the render spec, source/tool hashes, render telemetry, per-frame hashes, sequence self-hash, ffprobe JSON, video hash, attack results, three witness frames and the review MP4 if its size is practical for GitHub Pages. The full PNG sequence is disposable local work because its integrity can be represented by the tracked manifest plus selected witnesses; this retention policy does not permit claiming that absent PNG bytes are publicly re-verifiable.

## Explicit non-claims

- B14 does not test or satisfy the 4K Cycles master contract.
- H.264 is lossy; encoded pixels are not expected to equal PNG pixels.
- Frame completeness and container validity do not prove cinematic quality, temporal coherence, acting quality or physical realism.
- Disabling motion blur makes motion easier to inspect but is not a final-look choice.
- Same-machine evidence does not establish cross-platform determinism.
- Unkeyed hashes are not signatures or remote attestation.
- Published witness frames plus hashes do not make discarded full PNG source bytes independently reconstructible.

## Post-freeze additions

Any newly discovered requirement or failure will be labelled supplementary and added here without replacing or renumbering the frozen gates.
