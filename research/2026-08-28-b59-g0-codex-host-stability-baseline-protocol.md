# B59-G0 · Codex host stability bounded baseline protocol

Date: 2026-08-28
Status: PREREGISTERED
Parent commit: `098276e590f73cfef90906a80d41886c79c56adc`

## Purpose

Gate 0 begins with a safe measurement boundary, not an intentional crash reproduction. B59-G0 asks whether the current host can be sampled with a small, deterministic CLI result that is independently auditable and safe to return through the Codex desktop UI. It does not claim that one snapshot proves stability.

The user-provided crash report is frozen by SHA-256 `035649c3c49d8d95385f5221f968fd2824132d30184399ab204341542ef6d4b8`, 252,628 bytes and 1,323 lines. Its observed signature is `com.openai.codex` 26.820.80927 (7271), `EXC_BREAKPOINT (SIGTRAP)`, triggered thread `Chrome_IOThread`, with the main thread in `v8::ValueSerializer::WriteValue`. This narrows the investigation region but does not establish a unique cause.

## Safety boundary

The formal runner is read-only except for its fresh evidence root. It may launch at most twelve short local inspection children. It must not start Blender, render, use browser automation, access the network, call a model, invoke Docker, clean caches, send a signal, restart the host or restart Codex.

Raw process listings, crash JSON and system logs must not be printed. Runner stdout is a compact verdict envelope capped at 8,192 bytes. The complete receipt is capped at 65,536 bytes. Any command output consumed by the runner is bounded before parsing; an unexpectedly large or malformed response fails closed.

## Frozen admission thresholds

Disk admission is stricter than the unchanged B58 production rule. The host must expose at least:

`100 GiB core reserve + 0.5 GiB B58 projected write + 4 GiB stability margin = 112,205,053,952 bytes available`.

The added 4 GiB is an operational stability margin, not a relaxation or replacement of the production reserve.

Other admission requirements are:

- system-wide memory free percentage at least 25%;
- exactly one current Codex main process;
- no more than six Codex renderer processes;
- no single Codex renderer above 1.5 GiB RSS;
- total current Codex process-tree RSS no more than 4 GiB;
- zero active Blender processes;
- zero active B58 runner/compiler/auditor processes other than the inspection command itself;
- zero browser-automation processes.

Swap usage and orphan crashpad handler count are recorded as diagnostics but are not used as causal proof. Renderer count is explicitly not interpreted as browser-tab count.

## Evidence and audit

The runner writes one canonical self-hashed `results.json` in the fresh formal root. It records the frozen spec/parent/report identities, current app version, capture time, bounded host observations, exact gate vector, resource accounting and stdout/receipt size projections.

The independent auditor imports only Node built-ins. It reopens the spec, crash report and receipt; independently re-runs the safe host observations; verifies freshness, identities, arithmetic, process classification, output ceilings and self-hash; then applies all 24 registered mutations. It writes a canonical self-hashed `audit.json` and emits only a bounded summary.

## Interpretation

- `ADMITTED_FOR_LIGHTWEIGHT_WORK`: 20/20 gates and 24/24 attacks pass. This authorizes only further preregistered lightweight Gate 0 work.
- `BLOCKED_HOST_STABILITY`: integrity and audit are sound, but at least one resource/process admission gate fails. The blocker is retained; no threshold is lowered.
- `INVALID_EVIDENCE`: identity, output bound, self-hash or independent replay fails.

B59-G0 cannot close Gate 0 and cannot authorize the B58 official formal run. A later protocol must define repeated stability observations and any carefully bounded intervention/reproduction cells.
