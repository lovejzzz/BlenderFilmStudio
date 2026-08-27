# B52-D11.1 · Bounded nearest-integer temporal recovery holdout result

Date: 2026-08-27

Verdict: `BLENDER_NEAREST_INTEGER_TEMPORAL_RECOVERY_HOLDOUT_SUPPORTED`

Base failure: `null`

Preregistration commit: `08543cf17371966c9bb4963f8b78158906fe1f2f`

Tool-freeze commit: `8d94d677b9c8c266ccdf4532f3e74dd84f91fc00`

C1 preregistration / tool-freeze commits: `c81fcb8c92a4873e86a344562c20553d2284f441` / `e7a8ef5cb59e89f0fbc4462a032bf58adcdaf33c`

C2 preregistration / tool-freeze commits: `ac43e9074175a5b6a4192deb826ab448899efc23` / `add84222c218f27be772db3632c090127888c65f`

Formal result file SHA-256: `dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f`

Formal receipt file SHA-256: `643717651d4dafb48c87a5925391f06ef30ce97f62a8ab321d4c4aba62d0f443`

C2 audit file SHA-256: `35ef7e30f0f231262e58ee307cac4050e5e0137cbc1af209ac5d2ab7b1cb552f`

## Result

D11.1 supports one deliberately bounded recovery from D11's `MOTION_INTEGERIZATION` counterexample. For four fresh 199×109 textured orthographic fixtures, the real Blender 5.2 Vector pass was already within `1/1024` pixel of an integer at every component. An explicit whole-array nearest-integer quantizer converted those values to exact integral float32 motion before the inherited `int()` / `Math.trunc()` accumulator boundary. Python and Node produced byte-identical quantized arrays and byte-identical temporal outputs in all eight formal cells.

This result does not revise D11. D11 remains `BLENDER_REAL_TEXTURED_TEMPORAL_END_TO_END_HOLDOUT_NOT_SUPPORTED` for the unmodified composition. D11.1 is a new contract with a new transform, new fixtures, new tools and a new single formal execution.

## Formal execution

The admitted matrix created 81 unique child PIDs and no model or network calls:

| Operation | Count |
|---|---:|
| Blender 5.2 Cycles source processes / ray renders | 16 / 16 |
| Multipart adapter processes | 8 |
| Python / Node quantizer processes | 8 / 8 |
| Python / Node accumulator processes | 8 / 8 |
| Raw EXR encoder processes | 8 |
| Blender 5.2 compositor bridge processes | 16 |
| Independent analyzer processes | 1 |
| Total child processes / unique PIDs | 81 / 81 |

All 71 registered mutation attacks reached their frozen rejection reason. All fourteen ordered evidence gates were true. The formal root contains 533 files and occupies approximately 31 MiB; it was created once after accepted preflight and was not rerun during either audit correction.

## Quantization and semantic measurements

The maximum observed raw-to-integer error was `7.62939453125e-6` pixel, approximately 128 times smaller than the frozen inclusive radius of `0.0009765625` pixel. The radius was inherited from D10.1 before D11.1 output and was not fitted to these fixtures.

| Fixture | Valid / invalid pixels | Pixels recovered from toward-zero truncation | Semantic rejection |
|---|---:|---:|---|
| `QUANTIZED_OCCLUSION_OBJECT_XY_199X109` | 20,763 / 928 | 397 | layer disocclusion |
| `QUANTIZED_CAMERA_BOUNDS_199X109` | 18,042 / 3,649 | 661 | history bounds |
| `QUANTIZED_SAME_ID_DEPTH_DISCLOSURE_199X109` | 20,831 / 860 | 359 | same-ID depth disclosure |
| `QUANTIZED_TEXTURED_STATIC_CONTROL_199X109` | 21,691 / 0 | 0 | all valid |

Both source repeats produced the same values in every row. All sixteen declared 3×3 semantic probe patches were exact. Every moving-owner interior component equaled the analytic integer motion after quantization. Static motion serialized as positive float32 zero.

Every encoder input was recovered exactly from its Raw EXR. All sixteen fresh Blender compositor bridges retained the canonical resolved float32 arrays with zero changed scalars. The bridge proves Blender can carry the externally resolved result without changing it; it does not claim that Blender's compositor implements the quantizer or temporal algorithm internally.

## What the supported verdict means

The supported claim is narrow: when every finite Blender Vector component is independently observed to be within `1/1024` pixel of its nearest integer, the frozen whole-array quantizer can safely expose exact integral motion to this nearest-history temporal contract for the tested orthographic object motion, camera motion, layer disocclusion, same-ID depth disocclusion and static cases.

The quantizer rejects the complete array if any component is outside the radius. It does not clamp, partially emit, widen the radius, use fixture expectations or perform subpixel resampling. Exact and adjacent half-integers, NaN and infinities remain rejected.

## Audit correction chain

The original frozen audit completed its data replay but crashed before JSON serialization because replay-only `quantizerExact` retained NumPy `bool_`. It wrote no audit result and did not modify formal evidence.

C1 was preregistered before its new audit tool existed and permitted only an explicit native-boolean cast plus correction provenance. Its identity guard then correctly stopped before replay because the preregistered receipt SHA literal had been transcribed as 65 hexadecimal characters. Three independent hash implementations agreed on the immutable 64-character receipt hash above; `audit.json` remained absent.

C2 was again preregistered before its tool existed. It changed only the malformed receipt literal and C2 provenance identifiers while retaining C1's boolean cast and replay logic. C2 then passed:

- result and receipt identities exact;
- spec, preflight and process identities exact;
- eight analyzer replay cells exact;
- 48 diagnostic PNGs and 48 JSON sidecars exact;
- all fourteen evidence gates independently reconstructed true;
- all 71 registered attacks accounted for;
- verdict and base-failure order consistent.

The C2 audit's internal canonical `auditHash` is `c7fdf2f467e92c94cfd59a96881509b1fd87fc49d57a7e5d15f36b8be0570d40`. Its frozen tool SHA-256 is `648659fb934e60430b1f870a5d0e61cd7d6fde144ebb8de48f5be032b2f18700`.

## Non-claims

- No arbitrary float motion is declared safe. The domain remains no farther than `1/1024` pixel from an integer, per component.
- No perspective, subpixel, deforming-surface, transparency, volume, hair, motion-blur or depth-of-field reconstruction has been validated.
- Object Index is an opaque single-owner signal here; Cryptomatte coverage and multi-owner pixels are outside the contract.
- Temporal averaging was not shown to improve perceived image quality. This experiment validates dataflow and rejection semantics.
- No cinematic quality, character consistency, human preference or production authorization follows from this result.
- No cross-version, cross-OS, cross-CPU or cross-GPU equivalence is claimed.

## Next boundary

The next evidence-supported gap is not a wider rounding radius. It is a fresh perspective/subpixel reconstruction contract. That work must preregister how motion endpoints map to sample coordinates, how filtering and boundaries operate, which ownership/depth checks occur before and after reconstruction, and what analytic or supersampled truth can falsify the implementation. The current integer accumulator must remain frozen as a control rather than being silently generalized.

## Artifacts

- `specs/blender-nearest-integer-temporal-recovery-holdout.v0.1.json`
- `research/2026-08-27-b52-d11-1-nearest-integer-temporal-recovery-holdout-protocol.md`
- `research/2026-08-27-b52-d11-1-c1-audit-numpy-bool-correction.md`
- `research/2026-08-27-b52-d11-1-c2-receipt-hash-literal-correction.md`
- `experiments/blender-nearest-integer-temporal-recovery-holdout-preflight-v0-1/`
- `experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/`
