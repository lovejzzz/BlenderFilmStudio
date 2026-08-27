# B41-D3 · CPU/Vulkan render-backend control protocol

Status: preregistered before control tooling or output. This experiment cannot promote the B41 Eevee gate.

B41-D2 showed that default/explicit OpenGL and default/Mesa software-surfaceless combinations all reached `RENDER_STARTED`, emitted identical EGL errors and did not complete within 90 seconds. Blender's official history says Linux background mode should fall back to an EGL headless backend when other backends fail, while current Blender supports Eevee tests on Vulkan. The current image may nevertheless lack a usable device or software Vulkan driver.

B41-D3 reuses the exact current image with no build, pull, download, network or privilege expansion. A Cycles CPU control tests whether the worker can complete a real renderer without GPU context. A separate Eevee control forces Vulkan. Before rendering, the Blender Python process records only path existence/type for llvmpipe, Mesa EGL, lavapipe ICD and `/dev/dri`; it does not spawn another process.

If Vulkan Eevee completes, a later correction can isolate that route. If only Cycles CPU completes, the image/container is a viable CPU and compile worker but this host lacks an accepted Eevee route. If neither completes, the worker has a broader render problem. Every outcome remains non-promotable until a separate confirmatory protocol.

Primary references: Blender's official [Linux headless OpenGL/EGL change](https://projects.blender.org/archive/blender-archive/commits/commit/0322802314420fda3efee3c49c1a28102280ec05/source/blender/windowmanager), [Vulkan Eevee render tests](https://projects.blender.org/blender/blender/pulls/126784), and [Blender 5.2 GPU command-line options](https://docs.blender.org/manual/en/5.2/advanced/command_line/arguments.html).
