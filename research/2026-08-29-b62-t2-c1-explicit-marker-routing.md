# B62-T2-E1-C1 · Explicit timeline-marker camera application

Date: 2026-08-29
Status: PREREGISTERED — v0.1 retained; no tool changed; v0.2 absent

## Retained result

The first T2 run is permanently invalidated. It admitted the exact T1 scene and frozen tools, started one real Blender 5.2 process, and produced exactly `frame-0001.png` through `frame-0097.png`. Blender exited with code 1 after 10.676 seconds, at 463,618,048 bytes peak sampled RSS, with no wall/RSS/log/output breach. The root is 100 files, 25,860,818 bytes, tree SHA-256 `bdd2572775917ae0d4fbe80cd0d422ea273259618fc451b8e66b448b9c6b19d0`.

No complete render report, independent audit, video or scientific verdict exists. The 97 PNGs may not be reused or interpreted as T2 pixel evidence.

## Diagnosis

The boundary is exact: frame 96 is the last wide frame and frame 97 is the first medium frame. The renderer completed frame 97, then its post-render assertion found that `scene.camera` was still `CAM_WIDE_APPROACH` instead of `CAM_MEDIUM_CONTACT`.

This matches two previously retained Phase 0 isolated-scene animatic reports: both record `CAM_WIDE_APPROACH` at frames 97 and 193 despite correct timeline-marker bindings. In this Blender evaluation path, `scene.frame_set()` evaluates animation but does not imperatively copy a marker's camera into `scene.camera`. Markers encode routing; the render caller must apply the selected marker camera explicitly.

## Authorized correction

C1 changes no shot or threshold. For every frame, the renderer must select the latest marker at or before that frame, verify its exact name and bound camera against the frozen timeline, assign `scene.camera = marker.camera`, then render and record both identities. The independent Blender must derive the same routing from the source marker roster rather than trusting mutable `scene.camera` state.

The runner and Node auditor may bind this correction, bind the exact v0.1 failure tree, and move to the fresh root `experiments/b62-terminal-animatic-continuity-v0-2`. All 288 frames must be rendered again. Scene, camera transforms, cut frames, Eevee/color settings, all pixel/geometry/causal/video gates, resource ceilings, verdict mapping and `HUMAN_PENDING` remain unchanged.

This is an interface-semantics correction, not a scientific threshold correction.
