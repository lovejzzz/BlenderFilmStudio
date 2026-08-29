# B59-G0-R4 · Post-reclaim host-retention protocol

Date: 2026-08-29
Status: COMPLETED — ADMITTED FOR GATE 0 CLOSEOUT
Parent commit: `bcd0ee441a2178b8fd01b8a1477cafecc6619411`

## Trigger

D2 completed one authorized `default` Colima stop/start and restored the exact four-container workload. It recovered approximately 171.7 GB of host available space during the sampled window, while the two Colima sparse files accounted for only about 3.21 GB of reduced allocation. D2 was correctly rejected as formal evidence because its manifest incorrectly required byte identity for Colima's regenerated internal `lima.yaml`; its operational restoration and raw observations remain retained.

R4 does not repeat that intervention. It tests whether the restored, fully running workload retains the reclaimed capacity and whether the Codex host remains stable without any cleanup or mutation.

## Question

Across a 12-minute passive window, does the host retain disk capacity within the same 1 GiB loss ceiling that R3 failed, while preserving Codex PID/runtime continuity, bounded RSS, bounded browser temporary storage, and zero new Codex crash reports?

## Frozen design

R4 records seven immutable samples at least 120 seconds apart and spanning at least 720 seconds. The runner is the already-audited R3 longitudinal implementation, generalized only to accept an explicit spec path; the default invocation still points to the historical R3 spec.

The formal invocation is:

```text
BFS_STABILITY_SPEC=specs/codex-host-stability-post-reclaim.v0.1.json node scripts/run-b59-g0-codex-host-stability-longitudinal.mjs
```

The auditor uses the same explicit environment value. R4 performs no Blender, Docker, browser-automation, network, model, cleanup, signal or restart action. It writes only its bounded formal evidence.

## Frozen thresholds

- Available disk must remain at or above 250 GiB (`268,435,456,000` bytes) in every sample.
- First-to-last available-space loss must not exceed 1 GiB.
- Codex tree RSS must remain at or below 4 GiB, with first-to-last growth no more than 256 MiB.
- No renderer may exceed 1.5 GiB; renderer count must remain at or below six.
- Browser temporary filesystem allocation and growth must each remain at or below 64 MiB.
- The sole main Codex process must remain PID `26962`; PID `92848` must not return.
- No Blender, B58 worker or browser-automation process may run, and no new `ChatGPT*.ips` report may appear.

The disk-loss threshold is unchanged from R3. Raising the per-sample floor from the historical 104.5 GiB admission floor to 250 GiB protects the newly recovered capacity rather than merely avoiding imminent exhaustion.

## Interpretation boundary

A complete independent pass proves only a bounded 12-minute post-reclaim retention window. It is necessary but not sufficient for the goal's longer-term stability claim. Gate 0 may advance from `BLOCKED_DISK_RETENTION` to `SHORT_WINDOW_READMITTED`, after which a longer unattended observation and capacity guard must still be demonstrated before production rendering resumes.

Any failed gate is retained without threshold relaxation. If disk loss recurs, the exact sample window becomes the next attribution target. If the run passes, D2 is not retroactively converted into valid causal evidence.

## Formal result

R4 completed seven samples over `720,161` ms. The producer passed all 14 pre-audit gates, and the independent auditor passed all 15 final gates plus 20/20 registered mutation attacks. Final verdict: `ADMITTED_FOR_GATE0_CLOSEOUT`.

- Available-space loss: `130,621,440` bytes, approximately 12.2% of the 1 GiB ceiling.
- Minimum available space: `320,027,803,648` bytes, above the 250 GiB floor.
- Codex tree RSS change: `−27,344,896` bytes; maximum observed tree RSS `3,842,129,920` bytes.
- Maximum renderer RSS: `975,994,880` bytes across four renderers.
- Browser temporary filesystem: `20,480` bytes in every sample; growth `0`.
- Memory free percentage: minimum `87%`.
- Main process: PID `26962` in every sample; no new crash report.
- Results SHA-256: `4f7b7dbe2881b20301bee3a7c0897bfad43f7808b5788a09e22b7d247195bfe7`.
- Audit SHA-256: `f696592bfd8386d6b5696998072a987296655d252cd3b2384eeeefa2f67eb773`.

This closes the immediate R3 regression: under the restored workload, the same six-minute point no longer showed multi-gigabyte loss, and the full 12-minute window remained inside the frozen bound. Gate 0 is now `SHORT_WINDOW_READMITTED`, not fully closed. A longer unattended retention proof and an active capacity guard remain required before B58 production rendering resumes.
