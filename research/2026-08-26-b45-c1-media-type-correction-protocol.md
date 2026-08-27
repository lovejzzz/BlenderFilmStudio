# B45-C1 — single-layer EXR media type and null-analysis correction

Date frozen: 2026-08-26

Status at freeze: `PREREGISTERED_BEFORE_CORRECTION`

## Failure being corrected

B45 loaded all four compiled scenes and reached `RENDER_STARTED`, but the renderer attempted to assign `OPEN_EXR` while `image_settings.media_type` still constrained the format enum to `OPEN_EXR_MULTILAYER`. All four containers exited 1 with zero pixel files. The subsequent attack generator dereferenced a null report and prevented a machine-readable result.

## Allowed changes

1. Immediately before the single-layer EXR save, assign `image_settings.media_type=IMAGE`, then assign the already frozen `OPEN_EXR / RGBA / 32 / ZIP` settings. Record the applied save settings in every report.
2. Make the analyzer and attacks total over null report/decoded fields. A self-test must replace `TABLETOP-A1.report` with null, return `REPORT_SOURCE_TABLETOP-A1`, and not throw.
3. Write every corrected artifact under a new `-c1-` output root. Retain the failed B45 directory unchanged.

Nothing else may change. In particular, the two frames, 128×72 resolution, one Cycles CPU sample, exact decoded-float equality gate, four-container count, image identity, security limits, disk reserve and non-claims remain frozen.

## Promotion rule

C1 passes only if the complete original B45 analysis passes under the C1 evidence identity, both correction-specific attacks pass, the null-totality self-test passes, and an independent audit re-decodes all four EXRs. A successful output save alone is insufficient.
