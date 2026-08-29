# B59-G0-R3 · Longitudinal Codex host stability protocol

Date: 2026-08-29
Status: PREREGISTERED
Parent commit: `bc9d5b66815ccd507383e43981b44513d7f522e4`

## Question

After R2 admitted one post-restart snapshot, can the same Codex process remain inside the frozen disk, memory, renderer and RSS envelope across a bounded observation window without recreating the 46.9 GB browser temporary-filesystem leak or emitting a new Codex crash report?

## Design

R3 captures exactly four immutable samples. Adjacent samples must be at least 120 seconds apart and the first-to-last span must be at least 360 seconds. A sample more than 15 seconds late fails the timing gate; the runner may resume an interrupted observation but may neither backdate nor replace an existing sample.

### Preregistered correction C1: actual-capture interval anchoring

The first disposable rehearsal showed that fixed wall-clock due times can produce adjacent actual captures a few milliseconds below the minimum because the preceding sample itself finishes after its scheduled time. Before any formal R3 root existed, C1 changed each next due time to the later of its original wall-clock slot or the preceding sample's actual capture time plus the frozen minimum interval. This preserves the 120-second minimum and 360-second total span without changing either threshold.

The same rehearsal exposed that A05 used a hard-coded 1,000 ms forged interval, which equals rather than violates a one-second rehearsal spec. C1 defines the forged interval as the selected spec's minimum minus one millisecond. The production attack identifier and gate remain unchanged.

### Preregistered correction C2: synthetic-control sealing order

The C1 rehearsal passed all 14 pre-audit gates and all 20 attacks, but the auditor blocked its synthetic admissible control. Diagnosis showed that the control projected `EVIDENCE_BOUNDED_AND_SELF_HASHED` while the aggregate result still carried its pre-projection self-hash; the result was sealed only after projection, leaving a stale false gate in an otherwise valid control. Before any formal R3 root existed, C2 added an intermediate result seal before gate projection, followed by the existing final seal. No observed evidence, attack, threshold or production gate changes.

### Preregistered correction C3: non-circular result integrity

The C2 rehearsal proved that an intermediate seal cannot solve the deeper circularity: a result cannot use a gate stored inside itself to prove the validity of its own final hash, because changing that gate changes the hashed content. Before any formal R3 root existed, C3 aligned the auditor with the runner: `EVIDENCE_BOUNDED_AND_SELF_HASHED` projects start/sample bounds and hashes, while final-result byte count and self-hash are verified by the independent file-integrity layer and by candidate validation outside the result's own gate vector. Mutation A20 and direct self-hash validation remain fail-closed.

Each sample records current Codex version and app identity, main PID set, renderer count, maximum renderer RSS, total Codex-tree RSS, system-wide free-memory percentage, available disk bytes, browser temporary-filesystem allocated bytes and entry count, forbidden-process counts, and matching post-start Codex crash reports. Large process listings and file inventories are never returned to the UI.

## Frozen longitudinal limits

- Every sample preserves the R2 ceilings: available disk at least `112,206,020,608` bytes, free memory at least 25%, at most six renderers, maximum renderer RSS at most 1.5 GiB, and total Codex-tree RSS at most 4 GiB.
- Main PID must remain exactly `26962`; old PID `92848` must remain absent.
- Last-minus-first Codex-tree RSS growth must not exceed 256 MiB.
- Last-minus-first available disk loss must not exceed 1 GiB.
- Browser temporary-filesystem allocated size and first-to-last growth must each remain at or below 64 MiB.
- Blender, B58 workers and browser-automation processes must remain absent.
- No new `ChatGPT*.ips` diagnostic report may appear after the formal start time.

These are safety thresholds, not performance targets. A blocked result is retained and investigated; no threshold may be relaxed after observation.

## Crash-safe evidence contract

The formal root contains one immutable start receipt and one exclusive, self-hashed JSON file per sample. On restart, the runner validates every existing artifact and continues only from the next due index. It never overwrites a sample. Final results bind the ordered sample hashes and parent R2 evidence. The independent auditor replays current identity and filesystem/process state, validates every sample and runs all 20 registered mutations against a synthetic admissible control.

## Resource and stop policy

R3 starts no Blender, render, browser automation, network, model or Docker operation; performs no cleanup, signal or restart; and emits only bounded summaries. Any identity mismatch, excessive lateness, corrupt existing sample, ceiling violation, new crash report or evidence-size violation yields `BLOCKED_HOST_STABILITY`. A runner interruption leaves resumable evidence rather than a false pass.

## Decision boundary

`ADMITTED_FOR_GATE0_CLOSEOUT` requires 15/15 gates and 20/20 attacks. Passing R3 permits a separate Gate 0 closeout audit and a minimal B58 preflight; it does not itself authorize Blender execution. Failing R3 returns to targeted remediation with the frozen evidence intact.
