# B52-D12.10-P1-C1 owner-token pass result

Date: 2026-08-28  
Status: corrected post-hoc pass-transport result accepted  
Original real Blender renders: 8  
New Blender renders in C1: 0

## Result

`MATERIAL_INDEX_AND_CUSTOM_AOV_OWNER_TOKENS_VIABLE`

Both Blender 5.2 mechanisms transported compiler-assigned owner tokens through Cycles multilayer float32 EXR under the frozen stable-interior, display-invariance and clean-process-repeat gates. Object Index behaved as the preregistered negative control: both analytic owners remained exactly 7 and therefore could not be distinguished.

This result is a post-hoc mechanical correction over the eight immutable P1 EXRs. The failed original analyzer, invalid result and failure receipt remain preserved.

## Evidence identities

| Artifact | SHA-256 / self-hash |
|---|---|
| C1 specification | `5805af301077a8b3ae18892e3c4c2c5a2ad646a7e8b3cdddd762c39d22293a77` |
| C1 analyzer | `6deb4ca834f41b576a806f026e8388c9d9e6e9c8c58963a0019610f977b49a3b` |
| C1 audit | `64d1e080098e094fe9ad992122a63828220a06bbcc05a7ee06dc0ceef0dac6b8` |
| C1 runner | `2dcb6297d450682a97dd7d132c484fb1b79102dbea49227952d1ee14a321186b` |
| Result file | `3210641459a978e18cb2f71a2cd12b43e820edcd7bd4a1fe5d774e1f8179d3b0` |
| Evidence hash | `8de2871e551de8bbac1a87080042ba577735c6068b0e1850effbdd03cf4f02a2` |
| Audit file | `6890cf48b150702f022ad759ce297f63f1f9a244a6b5810619f1561fe5456c04` |
| Audit hash | `8b35f791c9eb7dacb6fbb4327c266bdb33870b8c41d6f6d4a19e61005fc9a202` |
| Receipt file | `a966bca4238a98faf4ee7279fcc8a1e443c1f3060e350f12d960722e7c0ce1e2` |
| Receipt hash | `11895973dcff014e317ad70e141e2b248a1efeda4202afea9ccae01e85ae5cfb` |

The analyzer passed 12/12 checks and 28/28 targeted mutations. The independent audit passed 14/14 checks, replayed 32 measurements, compared 24 raw-to-corrected payloads and 24 raw-to-original payloads, and verified the two new correction PIDs. C1 launched zero Blender processes, renders, model calls and network calls.

## Corrected stable-interior measurements

The corrected landscape projection uses a visible width of 8 world units and a visible height of `8 × 127 / 193`. For both moving frames, the independent analytic masks contain:

| Domain | Pixels per cell |
|---|---:|
| Background stable interior | 16,816 |
| Foreground stable interior | 5,727 |
| Frozen three-pixel boundary band | 1,968 |

Across all eight cells:

- Object Index is exactly `7.0` for every background and foreground stable-interior pixel.
- Material Index is exactly `11.0` for every background pixel and `23.0` for every foreground pixel.
- Value AOV is exactly `0.25` for every background pixel and `0.75` for every foreground pixel.
- All values are finite.
- Every tested data-pass float32 array is byte-identical between ACES SDR and Un-tone-mapped settings.
- Every tested data-pass float32 array is byte-identical between the two clean Blender processes.
- All 24 corrected extracted arrays are byte-identical both to the raw EXR parts and to the arrays retained by the failed original analyzer.

## Boundary behavior differs materially

Material Index remains categorical in the entire 1,968-pixel band: only `11.0` and `23.0` appear, with zero unregistered values.

The Value AOV is sample-filtered. In frame 0 it contains 658 non-token boundary pixels and 20 unique values; frame 1 contains 652 non-token boundary pixels and 20 unique values. The mixtures advance in `0.015625` steps, consistent with the frozen 32-sample render over a token difference of `0.5`.

This distinction matters:

- measured fact: Material Index provides a discrete owner label at these boundaries;
- measured fact: the Value AOV provides fractional coverage-like mixtures at these boundaries;
- inference: exact-equality temporal ownership should prefer Material Index for the first integration candidate, while treating AOV mixtures as invalid or as separately typed coverage evidence;
- unknown: neither mechanism is yet proven safe for H1 reconstruction at real moving boundaries.

## Engineering implications

Material Index is the narrower first intervention because it is already discrete and requires no new scalar decoding rule. The compiler must, however, own material pass-index assignment. An analytic owner using multiple materials must receive the same owner token across all its material slots, and a material data-block shared by different owners may need a compiler-created copy. Blender's measured RNA range is 0–32767, so allocation and exhaustion need explicit policy.

The custom Value AOV remains useful but cannot be treated as a categorical key by exact equality at antialiased boundaries. Scalar mixtures can also collide with another registered scalar token in a larger owner set unless the protocol reserves values and types mixed samples conservatively.

## Non-claims

- P1-C1 is post-hoc, not a fresh holdout.
- Pass transport viability does not prove temporal reconstruction quality or safety.
- Material Index does not automatically solve multi-material or shared-material ownership.
- Custom AOV injection is not proven safe for arbitrary third-party shader graphs.
- No D12.9-H1 verdict, perceptual quality, cost or production claim changes.

## Next falsifiable intervention

Preregister a fresh same-index temporal integration candidate that replaces Object Index ownership with compiler-assigned Material Index while leaving depth, alpha, vector, curvature threshold and all coverage/quality denominators unchanged. It must prove that the 15 accepted analytic-owner aliases are eliminated without creating new false accepts, and it must report the cost of discrete Material Index boundary rejection. The owner-aware one-sided curvature stencil remains a separate later intervention.
