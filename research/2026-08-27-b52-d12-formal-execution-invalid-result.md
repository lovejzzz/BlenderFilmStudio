# B52-D12 · Formal execution invalid before scientific decision

Date: 2026-08-27  
Status: `B52_D12_INVALID_BEFORE_FORMAL_DECISION`  
Scientific verdict: none

## What happened

The admitted B52-D12 runner created its formal root exactly once. All sixteen preregistered Blender 5.2 Cycles source processes completed, followed by the first multipart adapter and first Python reconstructor. The next child process—the Node reconstructor for `PROJECTIVE_OBJECT_DOLLY_TRANSLATE_107X67_R1`—exited before writing any output array or success report.

The retained exception is:

```text
ENOENT: no such file or directory, mkdir '.../reconstructors/node/PROJECTIVE_OBJECT_DOLLY_TRANSLATE_107X67_R1/arrays'
```

The frozen Node tool called `fs.mkdirSync(outputDir, {recursive:false})`. Its immediate parent cell directory did not exist. The synthetic contract test missed this because its temporary output directory had an already existing parent.

## Formal boundary reached

`run.failure.json` records eighteen successful child reports before the failed process:

- 16 `SOURCE` reports and real Cycles renders;
- 1 `ADAPTER` report;
- 1 `RECONSTRUCTOR_PYTHON` report;
- 18/18 completed PIDs unique;
- one additional failed Node process with no report and no output arrays.

No encoder, compositor bridge, analyzer or audit ran. There is no `run.receipt.json`, `results.json`, `audit.json` or diagnostic set. Therefore neither `SUPPORTED` nor `NOT_SUPPORTED` is authorized.

## Partial measurements are not a verdict

The first Python reconstructor had already completed before the infrastructure failure. It reported 5,841 valid pixels, maximum Vector endpoint error `2.2172927856e-5` px, correct-bilinear RMSE `5.0453673238e-5`, nearest RMSE `2.2481106718e-3`, wrong-sign RMSE `1.7630911654e-2`, and direct-depth-identity rejection fraction `1.0`.

Those values are retained because they exist, but they cannot satisfy any D12 gate: the second implementation, repeat, remaining fixtures, bridge, registered attacks and independent audit are absent.

## Allowed correction boundary

D12 itself will not be modified, resumed or overwritten. A C1 correction must be preregistered before its tool exists and may change only infrastructure needed to create the Node output's missing parent plus correction provenance/new-root routing. It must:

1. preserve the original science spec, fixtures, thresholds, projection formula, reconstruction math, validity rules and all unchanged tool blobs;
2. add a contract test in which both the cell parent and array directory are absent;
3. use a new formal root and execute all 65 successful child processes from scratch;
4. reuse no D12 source EXR, adapter array, reconstruction or report as a C1 measurement input;
5. retain this failed root and account for the rejected process separately from the corrected matrix.

## Evidence identity

- failed root: `experiments/blender-projective-subpixel-reconstruction-holdout-v0-1/`
- `run.failure.json` SHA-256: `ccb05339ec16b9d92350ad53552ae7368d2536e6e023bd0f1660ed9f7b67ec34`
- failed Node stderr SHA-256: `e822af5ab2cb0cfa7dbe7c6594755f5f768062a78d2659cf4b04ac4a5514ee5d`
- completed Python report SHA-256: `e2c94121c9d05f69b5c4f6b382418bb7d34e2f96e562e0bb23083dc46369d18b`

