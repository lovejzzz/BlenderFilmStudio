# PB.1 validation-only C2 attempt-03 retained failure

Date: 2026-08-31

Status: `FAIL` retained; independent failure audit `PASS` 36/36

Gate: PB.1 Repository and source identity

## Outcome

The exact v0.7 authorization and formal preflight passed. Attempt-03 consumed one local no-checkout engine clone, one pre-checkout engine-LFS objects symlink, one zero-network engine LFS materialization, one local dependency clone and one clean native build attempt. It performed zero public engine clones, product starts, renders, engine remote writes, LFS network transfers, releases, signing, notarization, DMG operations or PB.2–PB.7 work.

The C2 ordering correction succeeded: 6,669 engine LFS paths / 812,388,053 bytes materialized exactly, retained engine LFS storage remained unchanged, full strict fsck passed, the frozen 14-text-path `837/64` metric plus two former-pointer object transitions passed, and license/generated-path checks passed.

The run stopped at `CLEAN_NATIVE_BUILD` after 47.20 seconds with exit code 2. Peak RSS was 1,069,449,216 bytes; neither timeout nor resource ceiling caused the failure.

## Root cause

The exact dependency clone used `--no-checkout` under `GIT_LFS_SKIP_SMUDGE=1`, but the runner neither linked nor materialized the retained dependency LFS object store. The retained dependency has 622 LFS-tracked worktree paths backed by 618 unique local objects (1,070,190,055 bytes). In the fresh clone, all 622 paths remained pointers and the local dependency LFS store contained zero object files.

The first linker use rejected `zstd/lib/libzstd.a`: the fresh file was a 131-byte pointer for OID `b7063197d587191be8e8a475735bd8af3d805c265a6696b9a44b6b1ec6ba2006`, size 624,344; the retained object and retained worktree file both had that exact SHA-256/size and were valid archives. This is a harness dependency-materialization failure, not a film-engine source failure.

## Evidence

- evidence root: `experiments/ai-native-studio-phase-b/PB.1-2026-08-31-mac-m2max-attempt-03`;
- failure receipt hash: `8d624f8fbf8a295f6f00eef71408593b8335bc55992408b1d726fc5044c62cce`;
- verdict receipt hash: `a55c70c0a644c210fbc3e3569ba5c51b664f3aeab02daceb535719bbee0e078b`;
- build receipt hash: `0eba23eb89bebabd75fb0009adf21b0afcd6a9424ad8d62f24924618445c4f2c`;
- independent failure audit receipt hash: `5cba3132fb3cda14776291750a9d89a86ab365e32f14a5799387e14024b87e3c`;
- independent audit file SHA-256: `c96f1ac7f9a5fdf26b61a0a6a33d9ef6b0d388fc549a3158695e2ee07af50197`;
- independent auditor SHA-256: `f5fa99cdb4ab01cf887efe3cea1e8f15ee1a9654665fd4806e1ecfdf7d7d2e95`.

The independent auditor rehashed all nine JSON receipts and three build logs, reproduced the LFS pointer diagnosis, checked attempt-01/02 preservation, and verified the live public fork remained a single unchanged `main=4061e12bd45a2bec83e68d0cf49abbf56d4738f6` with zero tags, PRs or releases.

## Stop rule and correction boundary

Attempt-03 is immutable and must not be repaired or retried in place. A fresh correction may only add dependency-local LFS object access before dependency checkout plus one zero-network dependency materialization, while preserving the retained dependency object store. It must not modify film-engine source/ref/tag, perform any engine or LFS network write, or begin PB.2–PB.7.
