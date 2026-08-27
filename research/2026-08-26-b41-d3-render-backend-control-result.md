# B41-D3 · CPU worker confirmed; Eevee GPU route absent in current image

Verdict: `RENDER_BACKEND_CONTROL_COMPLETE_NON_PROMOTABLE`  
Classification: `CPU_ONLY_WORKER_CONFIRMED_EEVEE_GPU_ROUTE_ABSENT`  
Independent audit: `PASS`

## Cycles CPU control

The exact constrained C5 image completed a real Blender 5.2.0 LTS Cycles CPU render in `11039 ms`, exit 0. It wrote:

- `.blend`: `95671` bytes, SHA-256 `527d5d3a59355e14cde623574101851b30c7cc3c5efd4fa7173c2071abe46635`;
- 32×32 PNG: `2515` bytes, SHA-256 `d66e8befae87d66e999bfd4274d7d30ca0f1074df219b7c59afa7ff0f8da1fc4`;
- a passing runtime report identifying engine `CYCLES`, build `fbe6228777e7` and Blender `5.2.0 LTS`.

This directly demonstrates that the immutable image, amd64 emulation, Blender executable, OCIO, non-root/read-only/no-network launch boundary, input/output mounts and renderer output path work for a CPU renderer.

## Eevee Vulkan control

The forced-Vulkan Eevee control configured and saved its scene, then remained at `RENDER_STARTED` for `90084 ms`. TERM produced exit 143; there was no PNG/report. Its stderr repeated the same three `EGL_BAD_MATCH` messages as the OpenGL cells.

Both controls recorded the same pre-render inventory:

- `/usr/lib/x86_64-linux-gnu/libEGL_mesa.so.0`: present, `288248` bytes;
- `/usr/lib/x86_64-linux-gnu/dri/llvmpipe_dri.so`: absent at this probed path;
- `/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so`: absent;
- `/usr/share/vulkan/icd.d/lvp_icd.x86_64.json`: absent;
- `/dev/dri`: absent.

The missing llvmpipe path does not prove all Mesa software OpenGL components are absent; Debian may package software rasterization under a different filename. The absent lavapipe library/ICD and DRM device do show that the tested image has no observed Vulkan software ICD or hardware DRM device at the preregistered paths.

Independent audit matched every tool, milestone, artifact and classification. No build, pull, download or network operation occurred.

## Engineering decision

The current image is admitted for a separately preregistered compile-only / Cycles-CPU worker path. It is not admitted for Eevee rendering. A later Eevee route must either use a GPU-backed worker or rebuild/test a pinned software-Vulkan stack; neither claim is made here.

Official context: [Linux EGL headless fallback history](https://projects.blender.org/archive/blender-archive/commits/commit/0322802314420fda3efee3c49c1a28102280ec05/source/blender/windowmanager), [Vulkan Eevee tests](https://projects.blender.org/blender/blender/pulls/126784), [Blender 5.2 GPU options](https://docs.blender.org/manual/en/5.2/advanced/command_line/arguments.html).

Result SHA-256: `67ea4b0e51d43ab5936e8c6b6890e07aba97918979fa1f0e349c7e98402865ef`  
Audit SHA-256: `fa8f41464aebb54c78a4d4e824536d48724337226395bb893e731fbfc5419cda`

Artifacts: `experiments/linux-amd64-render-backend-control-v0-1/`.
