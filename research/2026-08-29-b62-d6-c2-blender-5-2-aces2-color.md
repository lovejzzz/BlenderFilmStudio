# B62-Q1-D6-C2 · Bind the Blender 5.2 native ACES 2.0 color contract

Date: 2026-08-29  
Status: PREREGISTERED — v0.1 and v0.2 retained; no C2 tool change exists yet

## What v0.2 falsified

C1 removed the explicit repository `OCIO` override, but the render process again exited before its first render call. A clean-environment, factory-startup probe of the same Blender 5.2 LTS executable reported the loaded scene's native values as `view_transform = ACES 2.0` and `look = None`; assigning `Medium High Contrast` was rejected. C1's assumption that bundled Blender 5.2 would restore the older AgX look roster was therefore false.

This agrees with Blender's current documentation: the bundled configuration includes ACES 2.0 support, and ACES view transforms are intended for photoreal film and television work. The correction is not an aesthetic optimization made after seeing validation images: v0.2 produced zero renders and observed no validation geometry.

## One permitted scientific correction

C2 supersedes exactly two base-spec fields:

- `render.viewTransform`: `AgX` → `ACES 2.0`
- `render.look`: `Medium High Contrast` → `None`

The render tool may explicitly assign those two values. The runner and auditor may bind C2, bind the immutable v0.2 failure and move to fresh v0.3. The builder and independent Blender tools remain byte-identical. The renderer may not change any other behavior.

Everything that can affect the camera hypothesis remains frozen: the selected motion-aware candidate, 96-frame bakes, eight newly unsealed frames, both conditions, 16 Cycles CPU renders, 960×540, 16 spp, 32-bit multilayer EXR, independent reopen/decode, geometry thresholds, pixel-difference gates and verdict mapping.

## Reproducible local runtime observation

The runtime check used an empty environment with only `PATH`, `LANG` and `LC_ALL`, then opened the fresh v0.2 derived scene under `--factory-startup`. Blender reported:

```text
VIEW_TRANSFORM_VALUE=ACES 2.0
LOOK_VALUE=None
Blender 5.2.0 LTS (hash fbe6228777e7)
```

The retained render receipt independently records the failed assignment, 0.523 seconds elapsed, 262,471,680-byte peak sampled RSS, zero completed render calls and no budget breach.

## Sources

- Blender Manual, Displays and Views: https://docs.blender.org/manual/en/5.0/render/color_management/displays_views.html
- Blender Manual, OpenColorIO: https://docs.blender.org/manual/en/5.0/render/color_management/opencolorio.html
- Blender 5.2 LTS rendering release notes: https://developer.blender.org/docs/release_notes/5.2/rendering/

## Interpretation boundary

If v0.3 passes, it supports or rejects only the motion-aware camera on the sealed D6 roster under the Blender 5.2 native ACES 2.0 diagnostic render contract. It does not establish final-film color grading, final-film image quality or full-sequence stability. Human review of all sixteen native-resolution PNGs remains mandatory.
