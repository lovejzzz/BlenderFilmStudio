# B62-Q1-D6 · Motion-aware camera sealed validation protocol

Date: 2026-08-29  
Status: PREREGISTERED — D5 v0.4 frozen; no D6 tool or formal root exists

## Research question

D5 found `RS_S200_E225`: retain the D4 target, −45° azimuth and 65 mm lens, but move radial scale from 2.00 to 2.25 with smoothstep across frames 193–288. The candidate passes the unchanged geometry template on all nine exposed derivation frames. D6 now asks whether it generalizes to the eight frames sealed before D5.

## Fresh paired scene

One fresh Blender process opens the immutable master and bakes two new cameras across all 96 integer frames. `STATIC` uses scale 2.0; `MOTION_AWARE` uses the frozen 2.0→2.25 smoothstep. Source camera data, action and timeline markers must remain unchanged. The process saves a new derived scene; no earlier D4 or D6 scene may be reused.

A second Blender opens that derived scene and renders only frames 198/210/222/234/246/258/270/282, both conditions, at 960×540 Cycles CPU 16 spp to multilayer EXR plus PNG. Both `scene.camera` and the active close-shot marker must route to the selected condition during each render and be restored afterward.

A third Blender independently reopens the scene, verifies both 96-frame bakes and scene invariants, measures the complete D3/D4 geometry template only on the eight newly unsealed frames, and independently decodes all 16 EXR Combined passes. The nine D5 derivation frames are forbidden as D6 validation measurements.

## Acceptance and limits

The motion-aware camera must pass all eight geometry rows without changing any threshold. Static-control outcomes are retained descriptively. All 16 images must be finite, non-empty and have positive dynamic range; each same-frame pair must have different decoded Combined pixels.

Technical and scientific results remain separate. If the full run is valid, eight motion passes support `B62_CLOSE_CAMERA_MOTION_AWARE_PASSES_SEALED_VALIDATION`; any motion failure yields the equally valid scientific rejection. Neither outcome is a cinematic-quality claim. All 16 native PNGs require labeled human review after machine audit.
