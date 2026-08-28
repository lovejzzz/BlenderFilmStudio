# B58-E1 · Restart-safe production orchestrator protocol

Date: 2026-08-28

Status: preregistered before any B58 tool or output exists

Parent: B57-E1 `PRODUCTION_DISK_JIT_READMISSION_SUPPORTED`

## Research question

B57 proves that the preferred production entry can re-check disk immediately before native Blender, bind that decision into the production receipt and fail closed before spawn. It remains a single uninterrupted command. If Codex or the orchestrator disappears after Blender has already completed, the current fresh-root admission cannot distinguish “completed and safe to skip” from “existing and unsafe to touch.” B58 asks whether an append-only, receipt-derived job state can make that distinction without trusting a mutable status file.

The desired property is deliberately narrow: on one local macOS host, a completed immutable stage is never spawned again; an incomplete or failed stage is never promoted and may retry only under a new attempt identity and empty root; a live or ambiguous process blocks duplicate work. This is the orchestration gate needed before spending render time on the cinematic proof.

## Frozen architecture

One immutable `job-manifest.json` binds the SceneSpec, expected BuildPlan, B57 production release, tool-freeze commit, ordered stage DAG, output roots and resource policy. State is reconstructed on every invocation from that manifest, a contiguous append-only event ledger and immutable stage/attempt receipts. No `status.json`, process memory or Codex conversation is authoritative.

The candidate production command is one `job:production` entry backed by `scripts/run-restart-safe-production-job.mjs`; `start`, `resume` and `status` all read the same immutable manifest and may not alter stage identities or semantics. The machine-readable spec freezes this entry, its ledger library, official preflight, single-use runner and independent auditor paths before any of them exists.

Every authoritative file is exclusive-created, self-hashed, fsynced and followed by a containing-directory fsync. Ledger events carry a six-digit sequence, prior-event hash, job/stage/attempt identities, payload and self-hash. Accepted bytes are never rewritten, renamed over, truncated or deleted.

The stage DAG is:

1. `PLAN_BIND`: compile the SceneSpec twice and durably bind byte-identical BuildPlan bytes;
2. `PRODUCTION_COMPILE`: call the unchanged preferred production compiler and accept only the complete B57 production/current receipt chain;
3. `VERIFY_RECEIPT`: call the unchanged preferred verifier and bind its result to the exact production receipt;
4. `FINALIZE`: independently recompute the complete ledger, receipt, artifact and resource-accounting closure.

“Exactly once” in this protocol means that a stage with a valid completed receipt is not spawned again inside this single-host job. It does not mean distributed exactly-once execution. Failed and abandoned attempts are not completed stages and may be retried only under a new ID and new empty root.

## Frozen recovery decision

Recovery must first verify the manifest, entire ledger prefix and every referenced receipt/artifact. It then applies exactly one rule:

- valid completed receipt: emit a `SKIPPED_VERIFIED` recovery event and spawn nothing for that stage;
- started without terminal receipt, exact process still live: return `WAIT_LIVE_PROCESS` and spawn nothing;
- started without terminal receipt, process dead, identity-mismatched or unverifiable: durably mark the attempt abandoned/non-promotable, then retry in a new empty attempt root;
- valid failed receipt: preserve it and retry only that stage plus unfinished descendants in a new empty attempt root;
- corrupt, discontinuous, conflicting or ambiguous evidence: `REFUSE_RECOVERY`.

A second resume after a valid final receipt must return the existing final receipt byte-for-byte with zero compiler, Blender or verifier processes.

## Frozen fault matrix

`BASELINE_B01` completes all four stages with one preferred production compiler, one native Blender 5.2 process and one preferred verifier.

`ORCHESTRATOR_EXIT_AFTER_COMPILE_B01` exits with code 86 only after the valid `PRODUCTION_COMPILE` stage receipt and corresponding ledger event have been fsynced, and before any `VERIFY_RECEIPT` start event. A separate recovery invocation must verify and skip both `PLAN_BIND` and `PRODUCTION_COMPILE`, start zero additional Blender processes, run exactly one verifier and finalize. The B01 plan and canonical structure identities must match the baseline pair.

`BLENDER_INTERRUPTED_B02` records the real native Blender identity and sends SIGTERM to its process group before completion; the existing budget supervisor may escalate only if the process does not exit. That attempt must terminate non-promotable and remain intact. Recovery must not repeat the already completed `PLAN_BIND`; it must create a new compile attempt/root, complete exactly one additional native compile, verify it and finalize. The interrupted output is never copied, linked, resumed in place or promoted.

`LIVE_PROCESS_REFUSAL` presents recovery with a started receipt whose exact controlled child identity is still live. The only valid outcome is `WAIT_LIVE_PROCESS` with zero duplicate compiler, Blender or verifier spawn. PID alone is insufficient: executable, process-start identity and argv hash must also match. Any ambiguity fails closed.

The full matrix permits four production compiler/native Blender starts: baseline, post-compile-crash, interrupted B02 and B02 recovery. Exactly three native compiles may succeed, one must be the controlled interruption, and exactly three preferred verifiers may run. Render, model, network and Docker operations remain zero.

## Independent audit and falsification

The independent auditor may import Node built-ins and shared canonical JSON primitives only; it may not import the orchestrator, recovery reducer or formal runner. It must reopen all authoritative bytes, rederive job state from the ledger, rerun the existing production/current receipt verifiers, recompute resource totals and independently inspect the process/fault records.

The machine-readable spec freezes 34 gates and 72 one-field semantic attacks across manifest identity, DAG shape, ledger continuity, event/receipt hashes, artifact rosters, completed-stage skipping, interruption quarantine, retry identity, live-process refusal, process identity, cost accounting and final closure. `SUPPORTED` requires 34/34 gates and at least 64 rejected attacks with no operation-ceiling breach. A duplicate spawn of a completed stage, promotion of a failed attempt, reuse of a dirty output, unsafe treatment of a live/ambiguous process or weakening of the B57 disk rule is an immediate `REJECTED`, not a bounded success.

## Execution order

1. Commit and push this spec, protocol and journal entry while all three B58 formal roots and every B58 tool path are absent.
2. Implement the ledger/reducer/orchestrator/auditor only after the preregistration commit is an ancestor of `origin/main`.
3. Use temporary development roots for syntax, reducer and fault-injection rehearsals. Preserve counterexamples and never patch a formal root.
4. Freeze final tool hashes in a separate pushed commit.
5. Run one zero-Blender official preflight on the three fresh registered roots and push it.
6. Invoke the single-use formal runner once. The post-compile exit case necessarily ends one process invocation; recovery is a separate invocation reading only durable bytes.
7. Audit, journal, commit, push and publish the result before beginning the cinematic proof.

At every preflight and native-spawn boundary, the unchanged B57 rule remains mandatory: at least 100 GiB free after a 0.5 GiB projected write. Preregistration observed only about 350 MB of headroom. If later disk usage consumes it, execution must pause before Blender until capacity is safely recovered; the reserve is never lowered.

## Claim boundary

B58 can support Codex-independent restartability because no conversational state is required for recovery. The controlled exit does not by itself prove every Codex desktop crash, power loss, kernel panic, filesystem corruption, concurrent writer or distributed scheduler mode. It does not render pixels or prove film quality. Its only purpose is to make the already supported production compiler safe to compose into the next, expensive cinematic sequence.
