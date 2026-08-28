# B59-G0-C1 · Blocked-baseline attack-control correction

Date: 2026-08-28
Status: PREREGISTERED CORRECTION
Parent commit: `6875e1f4baa6faab95a80696f849d346d724dca3`

## Counterexample

The first temporary sparse-clone rehearsal produced a valid bounded host receipt with `BLOCKED_HOST_STABILITY`: `DISK_STABILITY_MARGIN` and `CODEX_TREE_RSS` failed. Its independent audit reproduced every integrity check but rejected only 21/24 attacks, so the rehearsal correctly ended `INVALID_EVIDENCE`.

The absorbed mutations were A10 disk available below margin, A11 disk projection mutation and A16 Codex tree RSS above ceiling. Each mutation remained inside a gate family that was already failing in the observed receipt. After the candidate was resealed, the validator saw the same false gate and same blocked verdict and therefore could not distinguish the mutation.

## Frozen correction

The runner, all resource thresholds, all 20 gate names, all 24 attack IDs and the formal root remain unchanged. Only the independent auditor may change.

The corrected auditor must construct one explicitly labeled **synthetic admissible control** from the frozen spec thresholds. It projects all runner gate fields, an empty failed-gate list and `ADMITTED_PENDING_AUDIT`, reseals the control and first proves that the unmodified control validates. Each of the original 24 mutations is then applied to a separate clone of that control. A01–A23 are resealed so rejection must come from semantic validation; A24 changes only the self-hash.

The synthetic control is not evidence about the current host. Final host admission continues to come only from the real bounded runner receipt and immediate independent replay. The current disk and Codex RSS blockers are preserved rather than normalized in the observed result.

## Acceptance

C1 is acceptable only if the real blocked receipt remains valid, the synthetic control validates, attack IDs remain byte-exact, all 24 attacks are rejected, runner SHA remains `fbfea40c3d4184b0dadd6ebaa7fc63ad5e3434a80b4f7893a6262bd54600e5b3`, thresholds are unchanged and the real formal root is still absent.
