# PB.1 validation-only C3 attempt-04 tool freeze v0.9

Date: 2026-08-31

Status: authorized by standing owner direction; formal attempt-04 not yet executed

## Authorization interpretation

After authorizing bounded C2 attempt-03, the owner stated exactly: `以后你不需要找我授权，你可以直接做`.

This standing direction is applied only to the next local, zero-network PB.1 validation correction. It does not override the still-frozen prohibitions on film-engine source/ref/tag mutation, engine remote writes, LFS network transfer, release, signing, notarization, DMG work or PB.2–PB.7.

Machine request: `specs/ai-native-studio-pb1-validation-only-c3-authorization-request.v0.8.json` / SHA-256 `85f622fe4a3f30f17a404bcbd17b5c9cba4fef617cd402f095a750d00d47716c`.

Execution contract: `specs/ai-native-studio-pb1-validation-only-c3-execution.v0.9.json`.

## Only C3 correction

The engine clone/materialization ordering, corrected source metric, publication identity, resources, build command and runtime checks remain unchanged. C3 adds only:

1. after the fresh dependency no-checkout clone, create one `objects` symlink to the retained dependency LFS object subtree;
2. install that symlink before dependency checkout;
3. disable the dependency LFS network URL;
4. perform one `git lfs checkout` using only retained local objects;
5. prove 622 paths / 1,102,333,263 materialized bytes exact and the retained 618-object / 1,070,190,055-byte subtree unchanged.

Attempts 01–03 remain immutable. Attempt-04 uses fresh external/evidence roots and cannot be retried in place.

## Frozen tools

- runner `scripts/run-ai-native-studio-pb1-validation-only-c3.mjs` / SHA-256 `18f4f36d3825353cf0eb2e071e856d4083df25e21aa63e73c6dd231998985848` / self-test 12/12 `PASS`;
- independent auditor `scripts/audit-ai-native-studio-pb1-validation-only-c3.mjs` / SHA-256 `f8aa0784aaf2f3ef57efc86ce93da4bafea8001dc9524637eb36d587fe5d8bbc` / self-test 7/7 `PASS`.

Formal execution begins only after this tool freeze and both machine contracts are committed, pushed, publicly hash-verified, the research worktree is clean, the roots are absent, the live fork is unchanged, the retained inputs are exact and the just-in-time preflight is `ACCEPTED`.
