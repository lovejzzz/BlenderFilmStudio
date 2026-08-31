# PB.3 validation-only C4 attempt-03 retained pre-root failure

Date: 2026-08-31  
Verdict: `FAIL`  
Failure stage: `PRE_ROOT_AUTHORIZED_SCOPE_BINDING`

## Outcome

The exact C4 authorization was bound into a single-path execution commit,
`54965fc86a5ea4d867f394f31e87a7e58219272b`. The frozen runner then stopped
before creating either formal root and before starting Blender because
`stillUnauthorized[0]` differed from the corrected tool contract by one added
word, `this`:

- frozen: `without a separately committed exact execution contract`
- execution: `without this separately committed exact execution contract`

The remaining four entries were byte-exact, and the wording did not expand
authority. It nevertheless violated the frozen exact-equality gate. The
attempt is consumed and must not be amended or retried in place.

## Counts and disclosed deviation

The formal runner created no work/evidence root, started no Blender process,
and performed no proposal execution, BuildPlan write, scene build, workspace
save, reopen, render, engine edit, or engine remote write.

Before the runner, admission checking made one read-only `git ls-remote` call
to confirm `lovejzzz/film-engine` main. It observed the expected
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6` and wrote nothing, but it exceeded
the frozen zero-network ceiling. The retained evidence records this as one
network call; therefore attempt-03 is `FAIL` independently of the contract
transcription mismatch.

## Evidence

- Failure receipt: `experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-03/failure.json`
  - file SHA-256: `fa422b7336d87f95782d2fdd16a4ef9cd9c5d0d822724f47c62e63509b3ab200`
  - self hash: `248fb2bd86ecd42bca1ca269e1d2ce53e4ef20e11dd99db39f59e63b43c63413`
- Independent failure audit: `experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-03/audit-failure.json`
  - result: `PASS 22/22`
  - file SHA-256: `aecda60ef9675024b6cdf116b490e9a62938cab9a771643037c633f99e16fdfc`
  - self hash: `9c6c1cd7bc830b7ba23f95afe503d88a74ceeb9ec6cc3a802951feb397c081c7`

The audit independently proves the single-path execution commit, exact failure
leaf, absent work root, zero process logs/render-like artifacts, clean source,
accepted binary hash, and unchanged attempt-01/02 manifests.

## Next bounded correction

A future correction may only create a fresh attempt-04 contract whose
`stillUnauthorized` array is copied byte-for-byte from the already frozen C4
corrected tool. The C4 runner, helper, independent semantic auditor, exact
13-input roster, no-artifact predicate, resource limits, operation counts, and
all retained attempts remain unchanged. A fresh formal run requires a new exact
authorization; this failure grants none.
