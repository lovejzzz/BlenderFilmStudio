# B62-T2-E1-C5 · File-backed OIIO review adapter

Date: 2026-08-29
Status: PREREGISTERED — v0.5 retained; no C5 tool changed; v0.6 absent

The C4 retry passed admission and completed one active-production-Scene Eevee render, then stopped at 0.687 seconds with no retained pixel. Blender 5.2 reported `Image 'Render Result' does not have any image data` when the isolated output Scene attempted `Render Result.save_render`. This is not an output-Scene format error: the output Scene accepted PNG, but the headless source image contained no saveable RNA data.

C4's reasoning overgeneralized B61-D4. D4 proved an isolated Scene could save a generated image that already had pixel data; it did not prove that headless `Render Result` supplied such data. B61-D5 had already recorded the missing-data limitation and proved the narrower complete bridge: production multilayer EXR → pinned OIIO Combined RGBA decode → temporary ACEScg Blender float image → isolated review Scene PNG. C5 reuses that fully evidenced bridge rather than repeating the unsupported in-memory assumption.

The production Scene remains the sole active animation, camera, lighting and render context. Every frame receives exactly one Eevee render with `write_still=true` to one transient `scratch/current-frame.exr` under the fresh formal root. The renderer pins bundled OpenImageIO 3.1.13.1 and NumPy 2.3.4, extracts exactly one Combined RGBA quartet, records its float32 digest, flips OIIO top-first rows to Blender bottom-first storage, creates one temporary ACEScg float image, and saves the retained PNG through the non-active output Scene. The generated image and EXR are deleted before the next frame; the empty scratch directory and output Scene are deleted at completion.

The fresh root is v0.6. All 288 frames are regenerated. The final file roster is unchanged and contains no scratch artifact. The original fourteen scientific, process, capacity and HUMAN_PENDING gates remain unchanged; the adapter adds no render call, model call, network call, Docker process or Colima dependency.
