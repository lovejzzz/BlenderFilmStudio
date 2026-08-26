# OutputSpec and SceneSpec v0.1

Snapshot: 2026-08-25

Status: experimental, breaking changes allowed

## Research decision

The first executable project artifact is a restricted data contract between AI orchestration and a future deterministic Blender compiler. The model may propose SceneSpec data. It may not submit arbitrary Python, access the network, choose unrestricted paths, or directly mutate a production `.blend` file.

The contract is implemented as:

- `specs/output-spec.v0.1.json`
- `specs/scene-spec.v0.1.schema.json`
- `specs/fixtures/scene-spec-fixtures.v0.1.json`
- `scripts/validate-scene-spec.mjs`

## OutputSpec v0.1

The first output profile is a reproducible research master, not a theatrical DCP and not a claim of DCI compliance.

| Field | v0.1 decision |
|---|---|
| Raster | 3840 × 2160, square pixels |
| Frame rate | 24/1 fps |
| Reference shutter | 180° |
| Working encoding | scene-linear ACEScg |
| Master | multi-layer OpenEXR image sequence |
| Pixel type | 16-bit floating point (`HALF`) |
| Compression | ZIP lossless |
| Alpha | premultiplied |
| Required passes | Combined, Alpha, Depth, Normal, Vector, Cryptomatte |
| Required controls | exact frame count, finite pixels, channels, per-frame SHA-256, scene manifest, render telemetry, human review |

The exact ACES 2-compatible OCIO configuration and SHA-256 are intentionally unresolved. They must be pinned before Phase 1 rendering. A color-space name without the actual configuration and display path is insufficient.

## SceneSpec v0.1 root contract

The schema has ten required root blocks:

1. `shot` — ID, title, frame range, rational 24fps, meter units, seed, and active camera.
2. `assets` — stable ID, type, restricted URI, semantic version, SHA-256, license, transform, and visibility.
3. `actors` — character asset reference, rig profile, and identity lock.
4. `cameras` — lens, sensor, aperture, focus distance, shutter angle, transform, and optional restricted transform keys.
5. `lights` — type, scene-linear color, energy, size, and transform.
6. `world` — background color and strength.
7. `events` — contact, gaze, dialogue, and cue events with frames and subjects.
8. `render` — preview/final engine, resolution, samples, EXR encoding, AOVs, and output root.
9. `security` — network and Python denial, allowed asset roots, and operation allowlist.
10. `provenance` — brief, creator, UTC timestamp, and hashed/licensed sources.

Every object uses `additionalProperties: false`. Unknown fields are rejected rather than silently ignored.

## Validation layers

### L1 — JSON Schema

Checks required fields, types, constants, enums, bounds, patterns, unknown fields, and the exact contract version.

### L2 — Semantic validation

Checks relationships that are awkward or impossible to express locally in JSON Schema:

- `frameEnd >= frameStart`
- globally unique IDs
- active camera exists
- actors reference assets of kind `CHARACTER`
- event frames are inside the shot
- event subjects exist
- camera transform keys are inside the shot and strictly increasing

### L3 — Security validation

- Rejects absolute asset paths.
- Rejects URLs and URI schemes.
- Rejects `..` path traversal.
- Requires asset paths below `assets/` or `library/`.
- Requires outputs below `renders/`.
- Schema constants require `networkAccess: false` and `arbitraryPython: false`.

### L4 — BuildPlan and Blender verification (implemented 2026-08-26)

The compiler resolves and re-hashes local assets, verifies local provenance, calculates an immutable canonical BuildPlan, then verifies both the plan and assets again inside Blender 5.2.0 LTS. The first B01/B02 experiment is recorded in `research/2026-08-26-compiler-v0.1-experiment.md`.

## Fixture result

The suite contains eleven accepted and eleven rejected mutations of one B02 base document.

Accepted:

- Base B02 shot
- Title variant
- Lens variant
- Additional prop
- Additional fill light
- Valid character asset and actor
- Valid contact event
- Shifted frame range
- World-light variant
- High-sample non-denoised render
- Camera dolly keyframe variant

Rejected:

- Unknown root field
- Wrong schema version
- Reversed frame range
- Duplicate global ID
- Missing active camera
- Asset path traversal
- Network access enabled
- Missing asset license
- Event outside shot range
- Actor referencing a prop instead of a character
- Camera keyframe outside the shot

Result: **22/22 fixtures pass their expected accept/reject outcome.**

## Explicit non-claims

- The schema has compiled B01 and B02, but not a production scene or actor performance.
- The schema represents restricted camera transform keys, not general animation curves, retargeting, facial performance, material node graphs, simulation caches, or editorial conform.
- Structural determinism does not imply cross-GPU pixel identity.
- ACEScg and OpenEXR do not by themselves guarantee correct display or cinematic quality.
- A research master is not a DCP.

## Next milestone

The structural compiler milestone is complete. The next milestone is PixelSpec v0.1: pin the OCIO configuration and hash, render B01 plus three B02 frames to 4K multi-layer OpenEXR, inspect channels/metadata/finite values, and compare two clean renders.

## Primary references

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [OpenUSD introduction](https://openusd.org/release/intro.html)
- [OpenEXR Technical Introduction](https://openexr.com/en/latest/TechnicalIntroduction.html)
- [OpenEXR Standard Attributes](https://openexr.com/en/latest/StandardAttributes.html)
- [Blender 5.2 output properties](https://docs.blender.org/manual/en/5.2/render/output/properties/output.html)
- [Blender 5.2 color-management configuration](https://docs.blender.org/manual/en/5.2/render/color_management/system_configuration.html)
- [ACES 2 Output Transforms](https://docs.acescentral.com/system-components/output-transforms/)
- [DCI Digital Cinema System Specification 1.5.0](https://www.dcimovies.com/dci-specification/)
