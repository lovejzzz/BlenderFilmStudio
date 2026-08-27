# B52-D11.1 — Bounded nearest-integer temporal recovery holdout protocol

Date: 2026-08-27

Status: `PREREGISTERED_NO_FORMAL_TOOLS_OR_OUTPUT`

## Question

Can a narrow, explicit quantizer repair the one failed interface from D11 without broadening the system into an implicit subpixel renderer?

```text
fresh real Blender 5.2 textured multipart EXR
  → unchanged raw D10.1-style adapter
  → Python quantizer ─┐
                      ├─ byte-exact integral float32 motion
  → Node quantizer ───┘
  → inherited toward-zero accumulator semantics
  → Raw RGBA32 EXR encoder
  → Blender 5.2 compositor bridge
```

D11 remains immutable and `NOT_SUPPORTED`. D11.1 is a new experiment with new resolution, scale, names, IDs, meshes, materials, trajectories and probes. No D11 formal render or array may be reused in the D11.1 formal decision.

## Why a bounded quantizer

D11 observed correct raw Vector endpoints—the maximum error was about `1.079e-5` pixels—but showed that `int()` and `Math.trunc()` are discontinuous at integers. A value such as `12.999996185302734` satisfies the D10.1 endpoint tolerance and still becomes 12 instead of 13.

Unconditional rounding would hide a different error: it would silently reinterpret genuine subpixel motion such as 12.25 as integer motion. D11.1 therefore freezes a domain check before rounding:

```text
candidate(v) = v >= 0 ? floor(v + 0.5) : ceil(v - 0.5)
accept(v)    = finite(v) AND abs(v - candidate(v)) <= 1/1024
output(v)    = float32(candidate(v))
```

The `1/1024` radius is not fitted to D11's observed `1.079e-5` maximum. It is the already frozen D10.1 absolute endpoint-error ceiling. The check applies to every component in the complete motion array, not only favorable interior pixels. One rejected component rejects the whole array and produces no output payload.

Exact and adjacent half-integers are outside the accepted domain. The candidate rule is still specified as half-away-from-zero so the implementations have no language-default ambiguity. Zero is serialized as positive float32 zero, making `-0` observable and rejectable rather than visually equivalent.

## Independent implementations

Eight Python and eight Node quantizer processes run—one per fixture and repeat. They read the adapter's little-endian float32 bytes independently and may not import one another, D11 diagnostics or fixture expected motion. Their quantized payloads must be byte-identical, integral, idempotent and hash-bound to their input and report.

The accumulator continues to call Python `int()` or JavaScript `Math.trunc()`. Its input is now exact integral float32, so truncation must be an identity. This preserves the inherited accumulator semantics while making the inter-stage conversion explicit. It does not claim byte-identical D11.1 and D11 tool source because experiment identity and report wiring necessarily differ.

## Fresh fixtures

All four scenes use 199×109, orthographic scale 19.9 and nominal 10 pixels per world unit. The background is a 25.6×14.4 tessellated emissive plane with 0.8-world checker cells; foreground cells are 0.6 world. Probe centers were selected analytically in the top-left raster coordinate system and frozen before any D11.1 source render.

1. `QUANTIZED_OCCLUSION_OBJECT_XY_199X109`
   - raw expected Vector XY `[-16,+11]`, ZW `[-12,-9]`;
   - quantized D9 motion `[+16,-11]`;
   - one 3×3 valid moving-owner probe and one 3×3 layer-disocclusion rejection probe.
2. `QUANTIZED_CAMERA_BOUNDS_199X109`
   - raw expected Vector XY `[+13,-12]`, ZW `[+18,+8]`;
   - quantized D9 motion `[-13,+12]`;
   - one 3×3 valid camera-motion probe and one 3×3 bounds rejection probe.
3. `QUANTIZED_SAME_ID_DEPTH_DISCLOSURE_199X109`
   - foreground and background intentionally share Object Index 7505;
   - raw expected Vector XY `[-17,+8]`, ZW `[-11,-11]`;
   - quantized D9 motion `[+17,-8]`;
   - one valid mover probe and one revealed-background probe that must pass ownership and fail depth only.
4. `QUANTIZED_TEXTURED_STATIC_CONTROL_199X109`
   - expected raw and quantized motion `[+0,+0]`;
   - all 21,691 pixels must be valid, resolved=current exact, and quantized zeros must have positive-zero bytes.

Exact geometry, camera positions, material values, pass indices and probe centers are normative in `specs/blender-nearest-integer-temporal-recovery-holdout.v0.1.json`.

## Frozen rejection contract

The unit contract must exercise values at the boundary, one representable float32 just inside it and one just outside it, both signs, exact integers, signed zero, exact and adjacent half-integers, NaN and infinities. It must prove:

- inclusive acceptance at exactly `1/1024`;
- whole-array rejection immediately outside the radius;
- no output file or success report after any rejected component;
- toward-zero, floor and ceil substitutions are detected;
- Python and Node produce identical bytes and canonical hashes;
- a second quantization is byte-identical to the first;
- the quantizer never reads a fixture's expected motion.

The formal analyzer also independently recomputes the quantizer from raw bytes and refuses to trust either producer report.

## Inherited source, semantic and bridge contracts

- Blender 5.2.0 LTS `fbe6228777e7`, Cycles CPU, one sample, fixed seed 521111, four threads;
- adaptive sampling, denoising, motion blur, depth of field and persistent data off;
- Combined, Depth, Vector and Object Index in multipart RGBA32 ZIP EXR;
- typed RNA binary32 oracle only on enumerated float paths; all other structure exact;
- history valid only for in-bounds, equal Object Index, depth within `max(1,z)/1024`, and positive alpha;
- invalid pixels equal current float32 exactly; valid pixels receive one final float32 cast of the 0.5/0.5 average;
- Python and Node validity/resolved outputs byte-identical;
- encoded Raw RGBA32 ZIP EXR decodes exactly before two independent Blender compositor bridge renders.

The layer/depth removal and wrong-sign controls retain D11's minimum of 32 changed pixels and maximum absolute difference of at least 0.125. Diagnostic PNGs never participate in measurement.

## Formal boundary

| Stage | Processes | Blender renders |
|---|---:|---:|
| Source previous/current, 4 fixtures × 2 repeats | 16 | 16 Cycles |
| Multipart adapter | 8 | 0 |
| Python + Node quantizers | 16 | 0 |
| Python + Node accumulators | 16 | 0 |
| Resolved EXR encoder | 8 | 0 |
| Blender bridge, two repeats per encoded cell | 16 | 16 compositor |
| Independent analyzer | 1 | 0 |
| **Total** | **81 unique PIDs** | **32** |

Formal model calls and network calls are zero. Projected write is 72 MiB. Execution is admitted only when `freeBytes - 72 MiB >= 100 GiB`; preregistration does not waive that gate.

## Decision

`BLENDER_NEAREST_INTEGER_TEMPORAL_RECOVERY_HOLDOUT_SUPPORTED` requires every real input component to fall inside the frozen domain, both quantizers to agree byte-for-byte, quantized moving-owner motion to equal analytic truth, static zero to canonicalize, the inherited semantic and bridge chain to pass, all 81 PIDs to be unique, and every registered mutation to be rejected.

Any failure is retained with the earliest frozen base-failure label. An out-of-domain real Vector cannot be clamped or repaired; it requires a new diagnostic preregistration. A quantizer implementation mismatch requires an isolated cross-language experiment. D11.1 may not be revised or rerun after formal output.

If supported, the next boundary is not a larger integer tolerance. It is a separately designed perspective/subpixel reconstruction experiment with an explicit resampling kernel and new perceptual contract.

## Non-claims

D11.1 does not repair D11 retroactively, admit arbitrary float motion, validate perspective or subpixel resampling, cover deformation/transparency/hair/volumes/motion blur/depth of field, prove temporal image-quality improvement, establish cinematic quality or character consistency, generalize across runtimes, or authorize production rendering.

## Pre-tool state

At preregistration, all thirteen planned formal tool paths and the formal output root are absent. No D11.1 render, adapter array, quantizer output, accumulator output, EXR bridge output or diagnostic exists.

Frozen spec SHA-256: `c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a`.
