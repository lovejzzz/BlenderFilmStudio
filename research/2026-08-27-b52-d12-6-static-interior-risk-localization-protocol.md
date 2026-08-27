# B52-D12.6 static interior risk localization protocol

Date: 2026-08-27

Status: preregistered before diagnostic tools or output

## Why radius alone is no longer enough

D12.5-C2 showed that radius 3 removes exactly silhouette-distance ring 3 but leaves two fresh maxima unchanged. The wedge/panel maximum lies on the rear panel at distance 17; the crossing-rods maximum lies on the descending rod at distance 4. Both remain within production tolerance, but both violate the stronger twofold-headroom target. The thin foreground ring also loses too much per-owner coverage.

This falsifies a universal “first eligible ring causes the tail” explanation. D12.6 returns to arithmetic rather than increasing erosion again.

## Frozen read-only analysis

The only measurement inputs are the committed D12.5-C2 formal sources, adapters and paired consumer payloads. Repeat 1 is primary; repeat 2 is an exact-identity control. The invalid first-run root, D12.3 arrays and any new render are forbidden.

Before interpreting pixels, the localizer must verify parent file/internal hashes, the unchanged D12.5-C2 verdict, every report/payload binding and every reconstructed float32 byte for both radii. For every fixture/radius it must enumerate all tied maxima, then retain the top 64 samples with owner, silhouette distance, raw Vector bits, bilinear coordinates/weights, tap colors, signed contributions, pre-cast value, final float32 value and formal error.

## Candidate local risk bound

For each RGB channel, the preregistered bound is the sum of `abs(weight_i) × abs(previousTap_i − currentCenter)` over all four bilinear taps, plus one full float32 ULP at the pre-cast magnitude. Pixel risk is the maximum of the three channel bounds.

The bound is accepted as conservative only if it never underestimates any actual radius-interior RGB error across all six primary cells. Underbound count must be zero. Tightness, Spearman association, recall and selected-pixel fraction at the production gate and half-gate are report-only; D12.6 may conclude that a mathematically safe bound is too loose to be useful.

## Evidence boundary

One formal localizer and one independent audit run, with zero Blender processes, renders, model calls and network calls. The audit must reproduce every maximum, tied roster, float32 byte and aggregate, then reject at least eighteen registered mutations. A 4 MiB projected write must leave the unchanged 100 GiB disk reserve.

Success means localization and a conservative bound only. It does not validate an adaptive production rule or revise D12.5-C2. A fresh adaptive-gate holdout may be designed only after this diagnostic reports both safety and selectivity.

Machine-readable contract: `specs/blender-static-interior-risk-localization.v0.1.json`.
