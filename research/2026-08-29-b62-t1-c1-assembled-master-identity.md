# B62-T1-E1-C1 · Assembled-master identity correction

Date: 2026-08-29  
Status: PREREGISTERED — v0.1 retained; no correction tool change or v0.2 root exists

## Retained failure

Both independent BuildPlan compilations passed and produced the same 96-sample plan. The first real Blender process then stopped before adding or saving a camera because `CHAR_B62_GUARDIAN` in the assembled master did not equal the Phase 0 asset-library identity hash. The formal result is invalidated with a null scientific verdict. The v0.1 root is frozen as 6 files, 50,822 bytes and tree SHA-256 `2943c903…`.

## Root cause

The original gate conflated two identities:

- Phase 0 library hashes describe asset sources before master assembly.
- `B62_PHASE0_MASTER.blend` describes the admitted assembled production state.

A bounded read-only Blender inspection showed all three assembled collection manifests differ from their source-library hashes. The guardian has the expected master-only `COPY_LOCATION` contact constraint on `HAND_R_SOCKET`; the assembled core, set and character also carry material/animation state that is not the library baseline. The exact master file still matches its admitted SHA-256, so this is a contract-category error rather than evidence of file drift.

## Authorized correction

C1 preserves both layers instead of deleting either. Library hashes remain required provenance through the Phase 0 evidence. The exact master file hash plus the three now-frozen assembled manifest hashes become the compile-entry identity. Compiler and independent reopen must still prove those complete manifests, every existing action, contact/core/light samples, timeline and render/color state are unchanged before versus after the one authorized camera delta.

No camera sample, threshold, timeline, process count, resource budget, gate, attack or verdict changes. The BuildPlan compiler remains byte-identical. Runner and auditor additionally bind the retained v0.1 evidence and use only a fresh `v0-2` root.
