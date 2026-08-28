# B59-G0-C2 · Stability-margin total arithmetic correction

Date: 2026-08-28
Status: PREREGISTERED CORRECTION
Parent commit: `ae11980e0bcb02914d7bd1670fe4cfffb8abc385`

## Counterexample

The C1 rehearsal rejected all 24 attacks and reproduced every real-host integrity check, but its synthetic admissible control did not validate. Inspection found one preregistration arithmetic typo:

`107,374,182,400 + 536,870,912 + 4,294,967,296 = 112,206,020,608`

The parent spec and protocol instead recorded `112,205,053,952`, a deficit of 966,656 bytes. The runner already calculates the total from the three component fields, so its live disk gate was the stricter intended value. The redundant JSON total and prose were wrong.

## Frozen correction

C2 changes only the redundant `minimumAvailableBytes` value and matching protocol prose to `112206020608`. The 100 GiB core reserve, 0.5 GiB B58 projected write and 4 GiB stability margin do not change. Runner, auditor, gates, attacks, process ceilings and formal root do not change.

This correction tightens the mistyped total by 966,656 bytes and cannot convert the current blocked observation into an admission.

## Acceptance

The corrected total must equal the three components exactly. A new temporary sparse-clone rehearsal must validate the synthetic control, reject 24/24 attacks, retain all real host failures and produce either a credible `BLOCKED_HOST_STABILITY` or `ADMITTED_FOR_LIGHTWEIGHT_WORK` according to the new observation. The real formal root must remain absent.
