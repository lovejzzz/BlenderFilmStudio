# B45 first attempt — EXR media-type mismatch and null-analysis crash

Date: 2026-08-26

Classification: `INVALID_TOOL_INTERFACE_NO_PIXEL_DECISION`

The first command stopped before B45 because the common disk wrapper projected 20 GiB while the preregistered B45 projection was 1 GiB. The 100 GiB reserve was not changed. A second command explicitly supplied the frozen 1 GiB projection and passed the disk gate.

All four real Blender 5.2 Linux/amd64 containers then verified their source `.blend`, plan hash, source-scene hash, structure hash, shot seed and OCIO identity. Each reached `RENDER_STARTED`, exited 1 in 9,920–10,062 ms and wrote no EXR, PNG or report. The shared Blender diagnostic was:

`enum "OPEN_EXR" not found in ('OPEN_EXR_MULTILAYER')`

The compiled scene retained `image_settings.media_type=MULTI_LAYER_IMAGE`. The B45 renderer attempted to assign the single-layer `OPEN_EXR` format without first changing the media type to `IMAGE`. This is an output-interface defect, not evidence that the B44 scenes or Cycles renderer failed.

The runner then exposed a second defect: its adversarial attack generator assumed a successful report existed and dereferenced `report.source` when all four reports were null. It crashed before writing `results.json`. Raw stdout, stderr and milestone files remain under `experiments/codex-worker-pixel-promotion-v0-1/`; `failure.json` reconstructs the observed run from those files and the console receipt.

A correction may change only two things: set `media_type=IMAGE` before the single-layer EXR format, and make failure analysis total over null reports/decoded outputs. It must use a new output directory and preserve every frozen B45 frame, render setting, pixel exactness criterion, worker boundary and non-claim.
