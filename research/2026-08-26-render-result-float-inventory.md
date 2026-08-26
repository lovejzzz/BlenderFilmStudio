# Blender 5.2 Render Result / float-output inventory

Date: 2026-08-26.

Classification: **EXPLORATORY / INTERFACE VALIDATION / NOT CAUSAL**

Machine artifact: `experiments/render-result-float-inventory-v0-1/results.json`

## Question

Can B21 compare a scene-linear high-precision output and the existing display-referred PNG8 from one real Blender render, without pretending an unverified API cache is accessible?

## External contract

The Blender 5.2 manual states that Blender performs rendering/compositing in a scene-linear working space and recommends OpenEXR as the high-precision scene-linear intermediate format. It separately describes `Render Result` as displayed with the render view and `Save as Render` as the path that applies view/exposure/gamma when writing display formats.

Relevant official pages:

- `https://docs.blender.org/manual/en/5.2/render/color_management/color_spaces.html`
- `https://docs.blender.org/manual/en/5.2/render/color_management/displays_views.html`
- `https://docs.blender.org/manual/en/5.2/editors/image/image_settings.html`

The frozen B02 BuildPlan identifies its scene-linear encoding/role as ACEScg and pins the exact ACES 2 OCIO config SHA.

## Real Blender observations

The accepted probe used Blender 5.2.0 LTS build `fbe6228777e7`, the exact B02 `.blend`, receipt-bound OCIO, frame 110, Eevee 32 samples, dither 0, Fast GI on and TAA reprojection on.

After one `bpy.ops.render.render(write_still=False)` call:

- `bpy.data.images["Render Result"]` exists and reports `has_data=true`, `type=RENDER_RESULT`, `source=VIEWER` and `use_view_as_render=true`;
- in this background execution path, its RNA `size`, `channels`, `depth` and `pixels` expose zero/empty values, so direct `Image.pixels` float serialization is not an accepted measurement path;
- `Render Result.save_render` successfully wrote one PNG8 and, after changing only the file settings, one ZIP-compressed OpenEXR 32-bit output without a second render call;
- Blender-bundled OpenImageIO 3.1.13.1 decoded the EXR as 960×540, RGBA and `float`;
- the accepted EXR is `1,941,530` bytes, and the PNG is `426,950` bytes.

The final probe tool SHA-256 is `c24a4054…231e`; the accepted machine artifact records exact full hashes.

## Rejected attempts

1. The first command used `experiments/compiler-v0-1/.../scene.blend` instead of the receipt path under `compile-receipt-v0-1`; Blender rejected the nonexistent file. No result was accepted.
2. The second command rendered and wrote PNG, then the probe assumed `Render Result.pixels` was populated and called `min()` on an empty sequence. It exited nonzero and was rejected.
3. A third probe removed that assumption and confirmed the empty RNA access path. It was useful interface evidence but did not yet verify a high-precision output.
4. The accepted probe added a second `save_render` from the same Render Result and verified the resulting float EXR through bundled OIIO. It was then repeated with evidence paths so the exact outputs are preserved.

## Consequence for B21

B21 should be described as a **same-Render-Result dual-file localization experiment**, not as direct in-memory pixel access. Each experimental process must:

1. call the render operator exactly once;
2. save PNG RGBA8 under the frozen ACES 2 SDR view;
3. change only output file settings and save ZIP OpenEXR RGBA32 from the same Render Result;
4. compare decoded PNG pairs and decoded float EXR pairs separately at zero tolerance;
5. verify OIIO layout/format, all identities and the one-render/two-save report contract.

If EXR differs across replicates, variation exists before the PNG8 display/quantization output. If EXR is exact but PNG differs, the output transform/quantization path becomes the supported boundary. This does not by itself locate a Blender source line.
