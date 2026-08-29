# B59-G0-R3 · Longitudinal Codex host stability protocol

Date: 2026-08-29
Status: COMPLETED — BLOCKED ON DISK RETENTION
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

### Preregistered correction C4: spec-relative total-span mutation

The C3 rehearsal passed its synthetic control, 14/14 pre-audit gates and 19/20 attacks. A06 used a hard-coded forged span of 100 seconds, which violates the 360-second production spec but exceeds the three-second rehearsal minimum. Before any formal R3 root existed, C4 changed A06 to the selected spec's minimum total span minus one millisecond. The production threshold and attack identifier remain unchanged.

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

## Formal result

The single-use formal run spanned `360,135` ms across four immutable samples. Independent audit returned `BLOCKED_HOST_STABILITY`, 14/15 gates and 20/20 attacks. The synthetic positive control and every file/live integrity check passed. The sole failed gate was `DISK_RETENTION_BOUNDED`.

- Actual intervals: `120,029`, `120,057`, `120,049` ms
- Codex-tree RSS: `3,998,285,824` → `4,008,902,656` bytes; growth `10,616,832` bytes
- Maximum renderer RSS across samples: `874,987,520` bytes
- Memory-free range: 83%–86%
- Browser temporary filesystem: `20,480` bytes at all four samples; growth `0`
- Main PID: `26962` at all four samples; old PID absent
- New matching crash reports: `0`
- Available disk: `150,641,623,040` → `147,314,036,736` bytes
- Disk loss: `3,327,586,304` bytes, above the 1 GiB ceiling by `2,253,844,480` bytes
- `results.json` SHA-256: `e22542041fe1be1a7bd140567df0c657dda6a528754b75d21a6faf1a07407d95`
- `audit.json` SHA-256: `f85158a93341f62d14c59aee4b251eb373d901a953391f0c728e1a66fca15439`

This result supports post-restart Codex RSS stability and containment of the previously leaked browser temporary filesystem over the measured window. It does not close Gate 0 because the multi-GiB disk change is unexplained. The next phase is a read-only attribution experiment; no threshold relaxation or R3 rerun is authorized.
