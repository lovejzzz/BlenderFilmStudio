# B52-D11 — Real textured Blender temporal end-to-end result

Date: 2026-08-27

Verdict: `BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_NOT_SUPPORTED`

Base failure: `MOTION_INTEGERIZATION`

Independent audit: `PASS`

## What the experiment established

The complete frozen chain ran exactly once:

```text
real Blender 5.2 textured multipart EXR
  → raw D10.1-style pass adapter
  → inherited D9.1 toward-zero integer accumulator (Python + Node)
  → D8-style Raw RGBA32 EXR encoder
  → Blender 5.2 compositor bridge
```

The formal boundary contained 65 unique child PIDs: 16 Cycles source renders, eight adapters, eight Python accumulators, eight Node accumulators, eight encoders, 16 Blender compositor renders and one analyzer. All 56 registered attacks ran and passed. Forty diagnostic PNGs and forty bound sidecars were produced.

Every non-integerization base gate passed. Source multipart passes repeated exactly, adapter arrays matched independent reconstruction, Python and Node outputs were byte-identical, all semantic probes had the declared reason, sensitivity controls passed, the static fixture was 22,261/22,261 valid, and encoder/Blender bridge decodes reproduced the resolved float32 bytes exactly.

## Why the composition failed

The raw Vector endpoint measurements were numerically excellent. Across moving fixtures, p99 endpoint error was at most `8.529922399520072e-6` pixels and the maximum was `1.0789593218788873e-5`, far inside the frozen D10.1 limits.

That tolerance is nevertheless not sufficient for an integer consumer. Toward-zero conversion maps a value just below an integer to the adjacent pixel:

```text
12.999996185302734 → 12
-6.999996185302734 → -6
```

The owner-interior gate counted the same failures in both clean repeats:

| Fixture | Repeat 1 | Repeat 2 |
|---|---:|---:|
| object occlusion/disocclusion | 211 / 1,120 | 211 / 1,120 |
| camera bounds | 449 / 21,645 | 449 / 21,645 |
| same-ID depth disocclusion | 86 / 1,120 | 86 / 1,120 |
| static | 0 / 21,645 | 0 / 21,645 |

The formal sum is 1,492 mismatched owner-interior pixels across eight cells. The round-nearest diagnostic changed 87, 318 and 129 resolved float32 scalars per moving fixture repeat; it was forbidden from repairing D11.

## Audit interpretation

The independent audit replayed source, adapter, accumulator, encoder, bridge and diagnostic identities and returned `PASS`. Audit PASS means the negative verdict is internally reproducible; it does not turn the workflow into a supported one.

The audit also reports an 85,550-pixel broad mismatch sentinel. That field compares the moving-owner expected vector to every pixel in each moving frame, including static/background owners. It is intentionally used only as a nonzero verdict-consistency sentinel and must not be confused with the analyzer's preregistered owner-interior count of 1,492.

## Decision

D10.1 remains valid for pass extraction, D9.1 remains valid on analytic integer arrays, and D8 remains valid for Raw EXR transport. Their unmodified composition is not supported.

Per the preregistered decision rule, the only permitted recovery is a new D11.1 experiment that inserts an explicit nearest-integer quantizer between the raw adapter and integer accumulator, using entirely fresh fixtures. D11 will not be edited or rerun.

## Evidence identities

- Run receipt SHA-256: `dd75ba0e2f4a4b0ee950f9e12e84dc3f12265fe743a89370fb4f15f2643fc689`
- Result SHA-256: `490c569c4d12fe82ef49ff3d82d657512dbe297c69fd7f8f34df9b7daeeb31c8`
- Audit SHA-256: `4bd0e2081b831c75e5572c48c3b281e4a440e8d8f108fc50e1d774a878df6c2b`
- Audit internal hash: `c4cf8ed98dc53b97f024e885e38217081ea21a033ffdefca0aa8ca417bc0d76c`

Artifacts: `experiments/blender-real-textured-temporal-end-to-end-holdout-v0-1/`.
