# B62-Q1-D6-C1 · Restore Blender-native OCIO runtime

Date: 2026-08-29  
Status: PREREGISTERED — v0.1 retained; no C1 tool change exists yet

D6 v0.1 built the fresh dual-camera scene successfully, then the render process exited before its first render call. The runner had inherited D4's explicit repository ACES-v2 `OCIO` environment override, while the D6 base spec freezes Blender-native `AgX` plus `Medium High Contrast`. The external config exposes a different look roster, so Blender rejected the requested look.

C1 authorizes only removal of that runner environment override. Blender 5.2 then uses its bundled color configuration, where the preregistered AgX look belongs. The three Blender Python tools remain byte-identical. The Node auditor may change only to bind C1, bind the immutable v0.1 tree and use fresh v0.2.

No validation frame was rendered or geometrically measured in v0.1. The correction therefore does not use sealed outcomes, alter a threshold or change the candidate.
