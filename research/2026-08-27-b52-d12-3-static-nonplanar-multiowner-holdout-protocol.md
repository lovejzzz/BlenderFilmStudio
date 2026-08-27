# B52-D12.3 static nonplanar and multi-owner holdout protocol

Date: 2026-08-27

Status: preregistered before formal tools or output

## Why D12.2 is not enough

D12.2 supports a bounded static Vector/reconstruction tolerance on three opaque rigid planes, but a production scene is not one owner on one plane. Curvature changes depth and projected footprint across neighboring pixels. Multiple owners introduce discontinuities where a four-tap bilinear consumer can silently mix unrelated surfaces even when authored motion is zero.

D12.3 asks whether the unchanged D12.2 tolerance generalizes to owner-interior pixels on fresh curved, depth-varying and occluding scenes. It does not ask boundary pixels to behave like an interior surface.

## Fresh fixtures

The three fixtures are disjoint from D12.2 in raster, lens, sensor width, identifiers, pass indices, geometry and material parameters:

1. a nonuniform UV sphere beside a tilted torus;
2. a subdivided tilted rear grid partially occluded by a beveled front cube;
3. an icosphere behind a thin diagonal cylinder and a small front UV sphere.

All object, camera, topology and modifier state is identical at frames 0, 1 and 2. Each fixture has two fresh repeats and two rendered frames, for twelve real Blender 5.2 Cycles sources.

## Owner-aware decision domain

A current pixel enters the formal interior gate only when its Object Index is a registered positive integer, alpha exceeds 0.999, its entire Chebyshev-radius-2 current neighborhood has the same owner/alpha, and all four previous bilinear taps have that same owner/alpha. Cross-owner taps reject; they never blend.

Registered owner pixels excluded only by this erosion/tap rule form the boundary diagnostic set. Boundary count, owner roster, Vector maximum and reconstruction maximum/RMSE must be reported, but boundary magnitude cannot pass or fail the interior tolerance verdict. This prevents difficult boundary behavior from being hidden while avoiding an unjustified temporal-reuse claim across ownership discontinuities.

## Frozen gates

D12.3 carries the D12.2 engineering tolerance forward unchanged:

- interior Vector component maximum ≤ `1/4096 px`;
- interior reconstruction RGB maximum ≤ `1/524288`;
- interior reconstruction RGB RMSE ≤ `1/1048576`;
- static previous/current source RGB maximum = 0;
- at least 800 owner-interior and 50 boundary pixels per cell;
- exact source and consumer repeat identity;
- Python/Node payload identity and per-document typed-envelope identity.

Exact zero remains an orthogonal observation. No threshold may be widened after observing these fixtures.

## Evidence and process boundary

The three-layer D12.2 architecture is retained: exact consumer payloads, dual typed-envelope document integrity and one independent decision analyzer with no producer metrics. The single-use formal run permits exactly 55 unique child processes, zero model/network calls and a 16 MiB projected write. Admission requires at least 100 GiB free after projection.

Any infrastructure failure, missing coverage, owner roster defect, identity mismatch or analyzer crash invalidates the run and must be retained. A correction requires a new preregistration and fresh root.

## Non-claims

This remains static, opaque geometry. It does not authorize history reuse at owner boundaries and does not cover motion, deformation, transparency, hair, particles, volumes, motion blur or disocclusion. It is not a perceptual or cinematic-quality test.
