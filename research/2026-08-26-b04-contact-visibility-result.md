# B04 contact visibility diagnostic — result

Date: 2026-08-26

Status: original review camera **FAIL**; independent rear technical camera **PASS**

The frozen triangle-centre ray method was run on all 60 HOLD frames.

| Camera | Object | Minimum in frame | Minimum directly visible | Median directly visible | Gate |
|---|---:|---:|---:|---:|---:|
| Original `(2.45,-4.30,1.85)` | `HAND_R` | 100% | 0% | 0% | FAIL |
| Original `(2.45,-4.30,1.85)` | `PROP_BODY` | 100% | 16.7% | 33.3% | FAIL |
| Rear `(0,4.60,1.85)` | `HAND_R` | 100% | 25% | 66.7% | PASS |
| Rear `(0,4.60,1.85)` | `PROP_BODY` | 100% | 75% | 83.3% | PASS |

At frame 78 under the original review camera, all 12 hand triangle-centre rays hit `HEAD` first. This confirms that the geometry-pass clip was not valid evidence for a visible-contact review.

The rear camera is accepted only as a blinded technical-review candidate. The diagnostic does not claim good composition, performance, anatomy or cinematic quality.
