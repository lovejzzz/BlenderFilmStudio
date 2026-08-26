# B15 same-source review-proxy reproducibility result

Executed: 2026-08-26 against real Blender 5.2.0 LTS build `fbe6228777e7` and Blender-bundled OpenImageIO 3.1.13.1.

Status: **FORMAL EXACT FALSIFIED**

Run A and B used the same receipt-bound B02 `.blend`, ReviewRenderSpec, OCIO, Blender binary and renderer source bytes.

- PNG container equality: 0/144 frames;
- decoded RGBA equality: 127/144 frames;
- 17 frames contained any decoded difference;
- 114 of 74,649,600 sequence pixels failed exact comparison (`0.0001527%`);
- maximum absolute channel difference: `0.003921583294868469`, approximately one 8-bit code value;
- worst frame: 94, with 14 failed pixels;
- A sequence: `a52903fc327139ae41ed08f2d257d704b7977e9fda060138b106ceb56dbd56e4`;
- B sequence: `ad3b893019f1ae6f951d13b595b2d39f397e6af7e169e0279380edff61427139`;
- attacks: 8/8 passed.

Exact full-sequence Eevee proxy reproducibility is falsified on this machine. The magnitude is tiny, but B15 did not pre-register a perceptual tolerance, so it cannot be relabelled as a tolerance pass.

## Invalid attempts

The first Node launch failed before Blender because `realpath` was imported from `node:path` instead of `node:fs/promises`. After correction, the first complete comparison measured 126/144 exact decoded frames, but two SHA fixtures left a temporary `copy.png`; the extra-frame gate fired before the intended SHA gate, leaving 6/8 attacks. That candidate was `INVALID EXPERIMENT`.

The fixture extension was changed to `.tmp`; run B and comparison were regenerated. The final 8/8 result above is authoritative.

## Boundary

The data proves strict equality is too strong for this Blender 5.2 Eevee proxy path. It does not identify the source or prove that a viewer can perceive the difference. Eevee scheduling, color quantization and parallel floating-point evaluation require separate isolation experiments. No tolerance is adopted here.
