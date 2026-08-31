# PC.1 attempt-01 retained failure

Formal builder stopped before the first render, detail creation or save because the product engine correctly restricted `image_settings.file_format` to `OPEN_EXR_MULTILAYER`; direct `PNG` was unavailable. One Blender start occurred, with 0 render and 0 save. Frozen source SHA-256 remained exact.

Attempt-01 roots are retained. The only admissible correction is the already-established local output adapter: render internally to temporary multilayer EXR, decode the combined image to the same final PNG A/B roster, retain zero EXR, and keep all modeling, pixel, sentinel, operation and resource thresholds unchanged. PC.2 remains prohibited.
