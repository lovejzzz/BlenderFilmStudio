# B51-D2-C1 · EXR duration-parser correction

Date: 2026-08-27

Status before correction: `3/3 RENDERS COMPLETE · ORIGINAL CACHE RESTORED · ANALYZER EXCEPTION`

B51-D2 safely completed its cache intervention: the 79-file / 77,737,584-byte original tree was sequestered, a new 75-file cache was generated and retained, and the original path returned to its exact preflight content-tree hash. The analyzer then failed before producing `results.json` because Blender wrote `MM:SS.xx` EXR durations such as `00:00.78`, while the frozen parser required three colon-separated fields.

C1 may only accept both `MM:SS.xx` and `HH:MM:SS.xx`, bind that correction explicitly in the output, verify the original frozen tool blobs at the original tool-freeze commit, and replay the unchanged receipt and EXRs. It may not launch Blender, move either cache, rewrite the receipt, change a measurement or relax a gate.

The exception remains in `experiments/native-cycles-cache-state-derivation-v0-1/analyzer.initial-failure.json`.
