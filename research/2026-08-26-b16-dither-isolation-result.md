# B16 Blender output-dither isolation result

Executed: 2026-08-26 with real Blender 5.2.0 LTS build `fbe6228777e7`.

Status: **DITHER_NOT_SUFFICIENT**

Two new complete sequences were rendered after verifying the source scene started at `dither_intensity = 1.0` and setting only that property to `0.0` in memory. The frozen B14 renderer, ReviewRenderSpec, B02 `.blend`, OCIO and Blender bytes were unchanged.

- D0-A/B decoded exact: 130/144 frames;
- differing frames: 14;
- total failed pixels: 69 of 74,649,600;
- maximum channel error: `0.003921598196029663`, approximately one 8-bit code value;
- PNG container exact: 0/144;
- render time: 23.801723 / 23.682913 seconds;
- D0-A sequence: `fdfa9abc8716025c00b5d48c04d53b7262df301e5c7cc04f65479f926178e2b7`;
- D0-B sequence: `b82f55e94351865a757dfba372e572e002f24ab45ac165e2af0ed48042047cb8`;
- pre-registered attacks: 8/8.

Disabling output dithering did not restore strict pixel equality. Dithering alone is therefore insufficient to explain B15. The lower failed-pixel count than B15 is descriptive only: independent stochastic runs are not a paired estimate of improvement.

Frames 43, 91, 93, 110, 111 and 114 differed in both B15 and B16, often near similar coordinates. This makes render sampling/evaluation order a better next candidate than the PNG container.

No perceptual tolerance is adopted, and no conclusion is extended to Cycles EXR masters.
