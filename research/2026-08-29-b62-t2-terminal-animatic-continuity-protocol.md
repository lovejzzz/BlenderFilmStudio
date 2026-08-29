# B62-T2-E1 · Terminal 288-frame animatic and continuity protocol

Date: 2026-08-29  
Status: PREREGISTERED — T1 v0.3 frozen; no T2 tool or formal root exists

## Research question

T1 proves that the admitted scene package compiles into the intended production `.blend`. T2 asks the next materially different question: does that exact file survive every frame of the 12-second timeline, route all three shots correctly, keep its causal state, and maintain the D6 close-composition contract across all 96 close frames?

## Execution

One fresh Blender 5.2 process opens only the T1 scene and renders frames 1–288 at 640×360 with Eevee Next, 16 samples, motion blur and the pinned ACES-v2 display contract. It records the evaluated camera for every frame. No Phase 0 animatic image may be copied or reused.

A second fresh Blender reopens the same T1 scene, independently verifies the timeline/camera roster and causal state, decodes all 288 PNGs with bundled OpenImageIO/NumPy, and evaluates the unchanged material-aware D6 framing template on every close frame 193–288. It renders nothing.

FFmpeg encodes the exact image roster to a 288-frame H.264/yuv420p fast-start MP4; ffprobe independently verifies 640×360, 24 fps and 12 seconds. A Node auditor binds all parent, tool, runtime, process, pixel, geometry, video and resource evidence.

## Decision boundary

All 14 gates and all 96 close-frame geometry rows must pass. Machine success supports `B62_TERMINAL_288_FRAME_ANIMATIC_AND_CONTINUITY_SUPPORTED` but remains `HUMAN_PENDING` until the complete MP4 is watched and labeled. This stage detects broken routing, missing/corrupt/frozen output and geometric framing violations; it does not score film aesthetics or authorize claims about final Cycles quality.
