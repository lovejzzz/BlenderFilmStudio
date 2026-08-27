# B52-D12.6 first formal run is invalid

Date: 2026-08-27

Status: `INVALID_TOOL_FAILURE_BEFORE_RESULT`

The single frozen localizer process exited with code 1 before writing `results.json`. At an image-edge registered owner pixel, `reconstruct` called the bilinear-term helper before the preregistered bounds test; the helper attempted to read x=109 from the 109-pixel-wide wedge fixture.

No D12.6 result existed and no localization, error, risk, correlation or threshold measurement was inspected. Blender/model/network operation counts remain zero.

The failed root is retained at `experiments/blender-static-interior-risk-localization-v0-1/`. The only admissible correction is to preregister a new experiment identity and fresh roots, then move the tap read after coordinate eligibility without changing the registered arithmetic, samples, gates or decision logic.
