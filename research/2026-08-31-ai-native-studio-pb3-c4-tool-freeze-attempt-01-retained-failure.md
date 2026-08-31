# PB.3 C4 tool-freeze attempt-01 retained failure

Date: 2026-08-31

Verdict: `FAIL_STATIC_NEGATIVE_CONTROL_MESSAGE_ASSERTION`

The first inert C4 tool audit returned 31/32. All implementation, identity,
exact-diff, retained-root, no-power-import, resource, threshold and zero-count
checks passed. Runner self-test passed. The inert execution template exited 1
before creating either attempt-03 root and before starting Blender.

The sole false check was `inertTemplateRejected`. The static auditor required
stderr to contain `authorization text differs`, but the versioned runner
correctly rejected the draft contract at the earlier status gate with
`PB.3 C4 execution is not authorized`. This is an over-specific static-test
expectation, not an authority bypass.

The retained audit is
`experiments/ai-native-studio-phase-b/PB.3-c4-tool-freeze-2026-08-31-mac-m2max-attempt-01/audit.json`:

- file SHA-256 `890c64e41846c7dca83fa496a593ad0999735e6f45b459e766c82aa49cd757a1`;
- self hash `f2be8eb9bc4ada141e3137c3563c1ffddbbb636bb82a10db4c56e5c45bc704c5`;
- root manifest: 1 file, 3,084 bytes,
  `64aaedd8de5e45d55ecf72b5805ba1d1b41a5d35501f64754354cbb718a9a813`.

The C1 correction is preregistered at
`specs/ai-native-studio-pb3-validation-c4-c1-static-inert-rejection.v1.3.json`,
SHA-256 `cc57d8311dc2bf7cc67434f591ddd44ba5d183731d93dadc5bd648b66442948d`.
It permits one new static-auditor path whose only source change replaces the
expected message substring while retaining the nonzero-exit requirement.

The runner, independent auditor, Blender helper, corrected tool, authorization
request, all thresholds and all permissions remain byte exact. Attempt-03 roots
remain absent; Blender/proposal/BuildPlan/render/network/engine-write counts
remain zero. The failed root is immutable and must not be overwritten.
