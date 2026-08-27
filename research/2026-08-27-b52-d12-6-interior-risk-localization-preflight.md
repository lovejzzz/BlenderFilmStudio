# B52-D12.6 interior risk localization preflight

Date: 2026-08-27

Verdict: `ACCEPTED` — 10/10 preregistered preflight checks passed before the formal output root existed.

The frozen tool commit is `95389441e66aff5e6e5547fbab0bc593d5b790cb`. The analyzer, independent audit and preflight SHA-256 values are recorded in `experiments/blender-static-interior-risk-localization-preflight-v0-1/preflight.json`; its internal preflight hash is `82592c051fc09d1dbb4b9522a09237765cceedaa31f85b223d130ef01ed981fa`.

The preflight verified all named D12.5-C2 parent file and internal hashes, the Blender Python executable identity, absence of the formal D12.6 root, audit import independence, and 259 synthetic local-bound cases. Disk admission projected a 4 MiB write and left 107,549,319,168 bytes, above the unchanged 107,374,182,400-byte reserve.

No D12.6 formal measurement was executed or inspected during this preflight.
