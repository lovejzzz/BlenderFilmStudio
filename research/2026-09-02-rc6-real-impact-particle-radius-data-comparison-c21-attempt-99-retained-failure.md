# RC6 C21 attempt-99 — retained baseline-hash transcription failure

Date: 2026-09-02
Status: scientific result produced; independent audit retained `FAIL 22/23`

C21 copied all108 C20 cache files before reading them and measured every Data
and Mesh frame with zero Blender, bake, render, save, network or retained-root
write. Its frozen classification is
`C20_SAME_ONSET_MORE_SEVERE_THAN_C18`.

Both runs cross velocity support at frame24, Mesh expansion at frame24 and
particle support at frame25. The smaller radius therefore does not move the
measured onset. It increases maximum velocity support expansion from `173.84%`
to `769.48%`, particle support expansion from `32.38%` to `373.11%`, and Mesh
volume expansion from `51.54%` to `567.15%`. This is a same-onset amplification,
not an earlier instability.

The independent audit passes22/23. Its sole failed check is `c19EvidenceExact`:
the C21 spec transcribed C19 receipt self hash as ending `...5fea41d`, while the
committed receipt and all prior state record the exact value ending `...8a63de`.
The C19 result file/hash, receipt file hash, audit file/hash/status and every
other C21 evidence, process, cache, metric, classification and resource check
pass.

Attempt-99 remains immutable. A fresh audit-only C1 may correct only that one
JSON leaf and verify the retained root plus original sole-failure shape. It may
not rerun the analyzer, recopy the cache, invoke Blender or change the physical
interpretation.
