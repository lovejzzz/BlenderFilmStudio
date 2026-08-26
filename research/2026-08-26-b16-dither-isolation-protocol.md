# B16 Blender output-dither isolation protocol

Date frozen: 2026-08-26, before implementing the dither configurator or rendering either D0 sequence.

Status: **EXECUTED / DITHER_NOT_SUFFICIENT**

## Evidence-supported candidate

B15 held the complete proxy pipeline constant and found 114 failed pixels across 17/144 decoded frames. The maximum channel error was approximately one 8-bit code value. A real Blender query of the receipt-bound B02 scene then reported `scene.render.dither_intensity = 1.0`; the frozen B14 renderer does not override it.

This pattern makes output dithering a concrete candidate, not yet a conclusion.

## Intervention

The machine-readable contract is `specs/dither-isolation-spec.v0.1.json`.

Render two new clean sequences, D0-A and D0-B. Before invoking the exact frozen B14 renderer, a small Blender configurator must:

1. verify the scene starts at dither intensity 1.0;
2. set only `scene.render.dither_intensity` to 0.0 in memory;
3. emit the observed before/after values;
4. never save or modify the source `.blend`.

Every other ReviewRenderSpec field and exact tool/runtime/config input remains frozen. Both runs cover frames 1–144.

## Frozen gate

- both sequences pass receipt/source, frame-name, per-frame hash, dimension, camera/timeline and dither-before/after checks;
- D0-A and D0-B are distinct clean directories;
- OIIO compares all 144 RGBA pairs at zero thresholds;
- exact success requires 144/144 decoded frames exact, max error 0 and zero failed pixels;
- PNG byte equality is measured separately and is not required for decoded equality;
- the frozen B15 baseline remains 127/144 exact with 114 failed pixels;
- at least eight negative cases cover configurator identity, intervention value, alias directories, missing/extra frames, frame-byte mutation and comparison-artifact binding.

Decision labels are frozen as `CAUSAL_SUPPORT_DITHER`, `DITHER_NOT_SUFFICIENT`, or `INVALID_EXPERIMENT`. No post-hoc tolerance label exists.

## Causal boundary

If D0 becomes exact, B16 supports output dithering as a necessary factor in the B15 differences under this exact profile. It does not prove dither is the only possible Blender nondeterminism or that disabling it is visually preferable. If D0 remains non-exact, dithering alone is insufficient and the next isolation factor must be selected from measured evidence.

## Negative cases

1. configurator source hash mismatch;
2. requested intervention is not exactly 0.0;
3. configurator observes a non-1.0 starting value;
4. D0-A and D0-B alias the same directory;
5. missing D0-A frame;
6. missing D0-B frame;
7. extra D0-B frame;
8. mutated D0-B frame bytes.

Every case must reach its intended stable reason on disposable copies.

## Non-claims

- no perceptual or device-class tolerance is selected;
- no claim is made about banding quality;
- no Cycles EXR or master-output conclusion is made;
- no cross-platform conclusion is made;
- an exact D0 result does not prove all Blender operations are deterministic.

## Execution result

D0-A/B passed 8/8 attacks but only 130/144 decoded frames were exact. Fourteen frames contained 69 failed pixels; maximum channel error remained `0.003921598196029663`. The pre-registered decision is `DITHER_NOT_SUFFICIENT`.
