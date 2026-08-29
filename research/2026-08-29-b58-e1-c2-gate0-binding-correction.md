# B58-E1-C2 · Gate 0 binding correction

Date: 2026-08-29
Status: PREREGISTERED AFTER CANDIDATE TOOLING, BEFORE TOOL FREEZE OR OFFICIAL OUTPUT

## Why this correction exists

B58 candidate preflight, runner and auditor were implemented after the original B58/C1 preregistrations and exercised only in development roots. The user then made host stability Gate 0 a mandatory prerequisite because Codex had crashed and disk space had collapsed. B58 official execution was paused before its three registered roots existed.

Gate 0 has now closed with exact results/audit SHA-256 `588da9723eb7cfd7c611e2eb8122da1e6d29a93bee19e55c36eae85fbf0db54a` / `6d3a372f5fc3f07a3a154d22b8e9d124b264a8d4532db2fd5a777f3ed6395af7`, verdict `GATE0_HOST_STABILITY_CLOSED`, 15/15 gates and 20/20 attacks. The B58 candidate tools do not yet bind that later prerequisite. Running them unchanged would violate the current goal even if their original checks passed.

## Frozen correction

C2 replaces only the effective interpretation of parent gate `PREREGISTRATION_AND_TOOL_FREEZE_PUSHED` with `PREREGISTRATION_TOOL_FREEZE_AND_GATE0_CLOSED`. The 34-gate denominator remains unchanged.

Before creating any of B58's five production-preflight subroots, the official preflight must verify:

- exact Gate 0 results/audit paths and file hashes;
- valid result/audit self-hashes;
- exact final verdict, 15/15 gates, 20/20 attacks and no failed gates;
- the Gate 0 evidence commit is an ancestor of the selected B58 tool-freeze commit;
- the installed sentinel's latest/history records are self-hashed and linked, latest age is at most 1,200 seconds, severity is `HEALTHY`, available space is at least 250 GiB, browser temporary allocation is below 64 MiB and no alert exists.

The accepted preflight carries this Gate 0 receipt. The formal runner rejects a missing or mismatched receipt before materializing its formal root. The independent B58 auditor reopens Gate 0 evidence and validates the carried receipt.

Six C2 attacks cover results hash, audit hash, verdict, gate count, attack count and stale live-sentinel mutations. All six must be rejected in addition to the original 72 attacks and C1's 8/8 attacks.

## Unchanged boundary

C2 does not change any SceneSpec, BuildPlan, B57 byte, B58 stage, recovery rule, process ceiling, 100 GiB + 0.5 GiB disk policy, formal root, render policy or scientific claim. It does not retroactively call development probes official. Candidate tooling already exists locally but is not tool-frozen or tracked; all three official roots remain absent at registration.
