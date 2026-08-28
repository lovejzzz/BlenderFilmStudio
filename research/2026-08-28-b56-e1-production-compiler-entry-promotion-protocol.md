# B56-E1 · Production compiler entry promotion protocol

Date: 2026-08-28

Status: preregistered before production tooling, package aliases or output roots
Formal Blender renders: 0

## Why this is the next gate

B54 proved that a pushed zero-Blender preflight can authorize four fresh native Blender 5.2 compiles only after a durable attempt/admission/receipt sequence, while retaining B01/B02 BuildPlan and canonical structure identities. B54 was correctly rejected because the budget report did not persist the native child PID. B55 then made the minimal supervisor correction and passed 22/22 gates plus 41/41 attacks: all four native compile reports contain a locally observed positive child PID, and the preflight corroborates the schema with child-authored PID/PPID probes.

The remaining gap is operational, not another compiler-semantic hypothesis. The repository still exposes `compile:plan`, a low-level `compile:restricted`, and `verify:receipt`; it has no reusable preferred command that makes admission, durable authorization, compilation and a complete production receipt inseparable. The B54/B55 runners are immutable single-use experiments and cannot honestly be relabelled as a production API.

## Hypothesis

A minimal additive release layer can expose three preferred npm aliases—production preflight, production compile and production-receipt verification—without changing the existing SceneSpec compiler, admission module, budget supervisor, restricted compiler, CompileReceipt implementation, Blender compiler or artifact auditor. Four fresh alias-driven B01/B02 compiles should preserve the frozen plan and structure identities while proving that no requested output or native Blender process exists before pushed preflight evidence and a durable attempt/admission/receipt chain.

## Frozen intervention

Only these production changes are permitted:

1. add `specs/production-compiler-entry.v0.1.json`;
2. add the four production paths declared in the machine spec;
3. add exactly three package scripts with the exact command strings declared in the machine spec;
4. add the three B56 experiment tools.

Every other `package.json` byte and every frozen dependency hash remains unchanged. In particular, `compile:restricted` remains the low-level development/control path. B56 does not weaken or replace it; B56 adds the preferred auditable release path above it.

## Production authorization sequence

The production preflight validates a repository-relative SceneSpec and requested output, freezes their hashes together with the release/tool/runtime identities, compiles the BuildPlan twice in memory, applies the 100 GiB reserve gate, and writes one immutable self-hashed record. It starts no Blender process and creates neither attempt nor output root. The accepted preflight must then be committed and pushed.

The production compile command must perform this sequence:

1. exclusively create, write and fsync the sequence-1 attempt;
2. reopen the accepted pushed preflight through the unchanged admission module and require the exact SceneSpec, output, release and tool bindings;
3. exclusively create, write and fsync sequence-2 admission and sequence-3 attempt receipt;
4. only then create the requested output root and fsync sequence-4 formal-start;
5. compile the immutable BuildPlan and invoke the unchanged restricted compiler exactly once;
6. preserve its PID-bearing budget report and current CompileReceipt unchanged;
7. write one self-hashed production receipt binding the entire chain and all compiled artifacts.

On any admission rejection, the attempt root retains a self-hashed failure and receipt, the requested output remains absent, Blender process count remains zero and the command exits nonzero.

## Formal matrix

The official B56 preflight creates four accepted production preflights through `npm run preflight:production --`: B01-A, B01-B, B02-A and B02-B. It also exercises fail-closed negative cases for path escape, symbolic aliases, pre-existing output, dirty source/tool state, unpushed release state, output swapping and disk rejection. All preflight work is zero-Blender.

After the complete preflight root is committed and pushed, the single-use B56 runner uses `npm run compile:production --` four times. It then uses `npm run verify:production-receipt --` four times. The current CompileReceipt verifier must still report exactly 19 checks per run; all four PID reports must remain `BFS_BUDGETED_PROCESS_RESULT@0.2.0`; the frozen `.blend` auditor must reopen all four artifacts; B01/B02 plan and canonical structure bytes must remain pair-exact at the frozen hashes.

## Independent audit

The B56 auditor may not import any new production module or B56 runner/preflight module. It independently reconstructs package minimality, Git ancestry, sequence ordering, file/self hashes, BuildPlan and structure identity, PID schema, output roster, process counts and verdict. It may invoke only the preferred verifier alias as an external child. At least 48 registered semantic attacks must be rejected, including a stored-verdict flip with repaired self-hash.

## Capacity and safety

The 512 MiB projected write must leave at least 100 GiB free. Before this preregistration the host had fallen below that boundary. Under the user's existing exact cache-cleanup authorization, only rebuildable Adobe, Video Village download, Camera Raw, Telegram, Google and Codex workspace-dependency caches were emptied. Available space rose from 98,323,091,456 to 108,449,669,120 bytes; a later preregistration observation measured 108,446,367,744 bytes. Qwen models, Blender worker images, all Colima profiles and all repository evidence were preserved. The reserve was not lowered.

No in-app browser automation is permitted under the repository crash guard. B56 uses filesystem, Git, process receipts and non-browser verification only.

## Decision rule

`PRODUCTION_COMPILER_ENTRY_PROMOTION_SUPPORTED` requires every frozen gate, four preferred production compiles, four preferred independent verifications, both B01/B02 pair identities and at least 48 semantic attacks to pass. A clean scientific rejection is retained when one or more observed gates are false. A frozen tool or process exception invalidates the experiment with `scientificVerdict: null`; the same ID may not be repaired or rerun.

## Claim boundary

A supported result promotes a reusable, auditable compiler release entry. It does not prove deterministic `.blend` container bytes, render pixels, cinematic quality, full actor/cloth/hair/simulation coverage, cryptographic process identity or remote attestation. Representative production-scene coverage remains a separate later experiment.
