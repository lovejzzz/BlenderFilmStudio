# RC6 C36 attempt-118 — owner-requested restart interruption

Date: 2026-09-03

## Status

`INTERRUPTED_FOR_CODEX_UPGRADE_NO_SCIENTIFIC_VERDICT`

C36 had been frozen at research commit
`7a617d2bd4bea3be4171cba8419236257fef5b10` before execution. The owner then
requested a Codex upgrade while the one authorized REVIEW128 Data-only process
was running. The runner received an interactive interrupt and exited nonzero.
No matching runner, Blender or caffeinate process remained afterward.

## Retained partial roots

- work:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-03-native-phi-resolution-c36-attempt-118`
- evidence:
  `experiments/physical-richness/RC6-2026-09-03-native-phi-resolution-c36-attempt-118`
- work inventory at interruption: 32 files, 41,865,216 allocated bytes
- partial cache: 15 Data VDB files and 15 config files, ending at frame 15
- evidence inventory: admission plus two process logs, 8,192 allocated bytes
- Mesh files: 0
- PNG/JPG/JPEG/EXR/MOV/MP4 files: 0

The three evidence-file SHA-256 values at interruption were:

- `admission.json`: `f95f76b6190e91ad592651b401201d096cc7db2c5b0614407152f17a5d00fc25`
- `logs/blender.stdout.txt`: `c5b0f077ccdb974e5e5dbbd3bc5071d179a2c1e280066329dd82ef197f5cb88b`
- `logs/blender.stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Claim boundary and restart

Attempt-118 is incomplete, has no diagnostic classification and must never be
resumed, measured, repaired or presented as C36 evidence. Preserve both roots
unchanged.

After restart, run host preflight and create a versioned C36 C1 restart adapter
that changes only the fresh roots to attempt-119. Preserve the frozen
REVIEW128-versus-Preview96 question, exact R40/C34 inputs, thresholds, bundled
OpenVDB auditor, resource ceilings and zero-Mesh/zero-render boundary. Freeze
that adapter before creating either attempt-119 root, then execute once.
