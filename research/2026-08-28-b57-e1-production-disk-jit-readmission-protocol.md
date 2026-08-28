# B57-E1 · Production native-compile just-in-time disk readmission

Date: 2026-08-28

Status: preregistered; no B57 tool implementation or output existed when this protocol was written

Parent: B56-E1 `PRODUCTION_COMPILER_ENTRY_PROMOTION_SUPPORTED`

## Research question

B56 proves that a pushed, accepted production preflight can authorize a four-run native Blender compile chain. It does not re-observe free disk inside the production runner. If time passes between preflight and compile, the original capacity observation can become stale. B57 asks one bounded question: can the preferred production runner fail closed on a fresh disk observation immediately before restricted/native compilation, and can that decision become durable, receipt-bound evidence without changing scene semantics?

## Frozen hypothesis

After persisting the immutable BuildPlan and before spawning the restricted compiler, the production runner can:

1. call `statfs(repositoryRoot)`;
2. apply exactly the existing 100 GiB reserve plus 0.5 GiB projected write;
3. durably persist a sequence-5 disk admission;
4. refuse a newly insufficient host before any restricted or native Blender process starts;
5. bind an accepted observation into an upgraded production receipt and independent verifier;
6. preserve B01/B02 plan and canonical structure identities across four real Blender 5.2 compiles.

This is a TOCTOU-window reduction, not a claim that free space becomes immutable or reserved.

## Frozen intervention

- Preserve `specs/production-compiler-entry.v0.1.json` byte-for-byte as B56 evidence.
- Add a v0.2 release manifest that freezes the corrected production surface.
- Keep all three public package aliases and command strings unchanged.
- Add one JIT disk decision between BuildPlan persistence and restricted-wrapper spawn.
- The deterministic test ceiling may only lower the real observation. It is a rejection-only test affordance and cannot manufacture capacity.
- A rejected JIT decision must be durable and followed by invalidation evidence; wrapper/native process count must remain zero.
- An accepted JIT decision must be bound by file hash, self-hash and semantic fields into the production receipt and verifier.

SceneSpec parsing, BuildPlan compilation, restricted compile budgets, budget supervisor v0.2, current CompileReceipt semantics, Blender compiler and `.blend` auditor are unchanged controls.

## Frozen capacity rule

```text
minimum reserve   = 107,374,182,400 bytes
projected write   =     536,870,912 bytes
accept iff        = effective available - projected write >= minimum reserve
release override  = forbidden
```

At preregistration the real repository filesystem reported 108,723,322,880 available bytes and 108,186,451,968 bytes after projection, so implementation work is admitted. The formal negative case sets effective available bytes to 107,911,053,311—exactly one byte below the required reserve-plus-projection threshold—after a normally accepted preflight.

## Frozen ordering

```text
1 attempt fsynced
2 formal admission fsynced
3 attempt receipt fsynced
4 output formal-start fsynced
  immutable BuildPlan persisted
5 native-compile disk admission fsynced
  restricted wrapper spawn
  native Blender spawn
  current CompileReceipt
  production receipt with disk binding
```

The negative case is allowed to retain authorization, BuildPlan, rejected disk admission and invalidation evidence inside the already-authorized output root. It is not allowed to create restricted compiler output or start a restricted/native process.

## Frozen experiment matrix

The official preflight is zero-Blender. It must freeze the additive release and B57 tools, replay B56 evidence, keep SceneSpec 22/22 and B01/B02 dual BuildPlan bytes exact, pass the real host disk gate, and prove that the ceiling cannot exceed the real observation.

After accepted preflight evidence is committed and pushed:

- one `LOW_DISK_AFTER_ACCEPTED_PREFLIGHT` case must invalidate at `NATIVE_COMPILE_DISK_ADMISSION`, with zero restricted/native processes;
- B01-A, B01-B, B02-A and B02-B must each run through the unchanged preferred aliases on fresh roots;
- all four production verifiers and all four 19-check current receipt verifiers must pass;
- B01/B02 A/B plan and structure bytes must remain exact;
- no render, model, network or Docker operation is permitted.

## Frozen verdict mapping

- `SUPPORTED`: 26/26 gates pass.
- `BOUNDED`: stale capacity fails closed before spawn, but a non-safety accepted-run regression gate fails.
- `REJECTED`: stale capacity reaches a restricted/native process, the ceiling can raise capacity, the 100 GiB/0.5 GiB policy is weakened, or durable receipt binding fails.
- `INVALID`: parent/tool/freshness/pushed-evidence ordering or operation accounting cannot be established.

The independent auditor must reopen bytes directly, import no production/B57 execution module and reject at least 56 preregistered semantic attacks.

## Claim boundary

B57 does not rewrite B56, reserve filesystem blocks, eliminate all concurrent-writer races, render pixels, prove cinematic quality, sign receipts or remotely attest a process. If the result is supported, the next question is whether an observation-to-spawn receipt is sufficient for the single-host threat model or whether explicit block reservation is necessary.
