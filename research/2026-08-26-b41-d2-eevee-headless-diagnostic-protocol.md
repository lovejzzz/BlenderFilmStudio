# B41-D2 · Eevee headless/backend diagnostic protocol

Status: preregistered before diagnostic tooling or output. This experiment has no worker-promotion authority.

B41-C5 saved the scene and reached Eevee rendering, then emitted `EGL_BAD_MATCH` and exceeded the frozen 30-second success boundary. Blender's 5.2 API documents `BLENDER_EEVEE` as the render-engine value. The Blender manual characterizes Eevee as GPU-based and documents explicit `--gpu-backend` choices including OpenGL.

B41-D2 reuses the exact already-built C5 image by immutable ID; image build, pull and archive download are prohibited. Four cells cross default versus explicit `--gpu-backend opengl` with default versus `EGL_PLATFORM=surfaceless` plus `LIBGL_ALWAYS_SOFTWARE=1`. Every cell keeps the B41 security and resource boundary, receives 90 seconds plus a five-second termination grace, and writes ordered milestones around scene configuration, `.blend` save, GPU probe, render and report.

The result classifies whether baseline merely needs more time, the software-surfaceless environment is required, explicit OpenGL is required, another tested combination completes, or none completes within the diagnostic ceiling. A completed cell still cannot change the B41 30-second contract or promote the worker; it only supports a later preregistered correction decision.

Primary references: [Blender 5.2 RenderSettings API](https://docs.blender.org/api/5.2/bpy.types.RenderSettings.html), [Eevee limitations](https://docs.blender.org/manual/en/5.2/render/eevee/limitations/limitations.html), and [Blender 5.2 command-line arguments](https://docs.blender.org/manual/en/5.2/advanced/command_line/arguments.html).
