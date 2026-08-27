# B41-D2 · No tested headless configuration completes Eevee

Verdict: `EEVEE_HEADLESS_DIAGNOSTIC_COMPLETE_NON_PROMOTABLE`  
Classification: `NO_COMPLETION_WITHIN_DIAGNOSTIC_CEILING`  
Completed cells: `0/4`  
Independent audit: `PASS`

## Four-cell result

All cells reused image `sha256:c4b0f6bebe77e9bd10b4875aaf0500d798de081259397c525f923f7a9eea35b1` without build, pull or archive download. Each ran as the frozen non-root user with read-only root, no network, empty capabilities, `no-new-privileges`, and the same CPU/memory/PID limits.

| Cell | GPU backend | Headless environment | Exit | Elapsed | Last milestone |
|---|---|---|---:|---:|---|
| B00 | default | default | 143 | 90095 ms | `RENDER_STARTED` |
| B10 | explicit OpenGL | default | 143 | 90088 ms | `RENDER_STARTED` |
| B01 | default | Mesa software + surfaceless | 143 | 90095 ms | `RENDER_STARTED` |
| B11 | explicit OpenGL | Mesa software + surfaceless | 143 | 90093 ms | `RENDER_STARTED` |

Every cell completed scene configuration and `.blend` save. Every pre-render GPU probe returned `SystemError: GPU functions for drawing requires the gpu module to be initialized. See gpu.init.` Every render then emitted the same three `EGL_BAD_MATCH` messages, produced no PNG/report, reached 90 seconds, received TERM and exited 143 without requiring KILL.

The software/surfaceless environment and explicit OpenGL therefore had no observed effect on completion, milestone boundary or error signature. This result rejects the four tested configurations on this ARM64 Colima + qemu testbed. It does not prove that every X server, Wayland compositor, Vulkan software device, native x86-64 host or GPU worker would fail.

Independent audit matched tool hashes, every milestone and partial artifact, the classification and non-promotion state.

Official context: Blender 5.2 documents `BLENDER_EEVEE` as the render engine, describes Eevee as GPU-based, and exposes explicit `opengl`, `vulkan` and `metal` GPU backend values: [RenderSettings API](https://docs.blender.org/api/5.2/bpy.types.RenderSettings.html), [Eevee limitations](https://docs.blender.org/manual/en/5.2/render/eevee/limitations/limitations.html), [command-line arguments](https://docs.blender.org/manual/en/5.2/advanced/command_line/arguments.html).

Result SHA-256: `7a448ce9fc5f92bdd170258adf7c7ef4c46d1a1d25cfdd02e8eea71e32b24348`  
Audit SHA-256: `35e0df8ef9b33a35a76695c726052fd79f5d18cae254078904a1c035f6b35533`

Artifacts: `experiments/linux-amd64-eevee-headless-diagnostic-v0-1/`.
