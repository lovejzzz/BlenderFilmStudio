# B62-T2-E1-C4 · Render Result to isolated PNG output adapter

Date: 2026-08-29
Status: PREREGISTERED — v0.4 retained; no C4 tool changed; v0.5 absent

The C3 retry stopped in 0.485 seconds before any render. Blender 5.2 reports that the production Scene's dynamic image format enum contains only `OPEN_EXR_MULTILAYER`; assigning `PNG` is illegal while that data block is in its multilayer-image state. This is the exact behavior already isolated by the retained B61 PNG export-context probe.

C4 does not retreat to the frozen isolated renderer. The exact production Scene remains the active animation and render context. Each frame renders to the in-memory `Render Result` with `write_still=false`. A separate non-active Scene is configured only for PNG/RGBA/8 storage and pinned display/view/look; `Render Result.save_render` writes the PNG through that adapter. The adapter is removed after the sequence and contributes zero render calls.

The fresh root is v0.5. All 288 frames are regenerated, source bytes must remain exact, and every original scientific and resource gate remains unchanged.
