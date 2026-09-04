# Audio C4 uses the same meter before and after gain

Retain C3 as audio FAIL: video unchanged, but-15.1LUFS/-2.5dBFS. Read-only analysis establishes a meter discrepancy on this sparse original WAV: loudnorm reports input-32.19LUFS, while the independent ebur128 meter reports-27.3LUFS. The12.19dB gain correctly produces approximately-15.1 according to ebur128. This is not evidence for changing the acceptance range.

Correct the input measurement to the same complete ebur128 integrated-loudness/true-peak calculation used for final acceptance. Apply the unchanged constant-gain formula; source values-27.3/-14.7 imply7.3dB. Fresh PF-AUDIO-C4-2026-09-04-attempt-01 roots, same source WAV, exact video packet copy, all earlier limits and no Blender or retained writes. Keep the original loudnorm/C1/C2/C3 measurements. Product future export must use this matched measurement method.
