# F0 evidence roots

This directory indexes immutable `F0-SOURCE-FEASIBILITY` runs. Do not place the
Blender source checkout, dependencies or build products here.

Create one directory per host and attempt using a stable identifier such as:

```text
F0.1-<utc-date>-<host-id>-attempt-01/
```

Each root must contain its preregistration, read-only host preflight output,
exact source/toolchain identity, command transcript, resource measurements,
artifacts or artifact hashes, audit, and final `PASS`, `FAIL`, or `BLOCKED`
verdict. A retry creates a new root and cross-binds the earlier receipt.

The normative acceptance criteria are in
`specs/ai-native-studio-f0.v0.1.json`.

## Current result

`F0.1` is `PASS` on the 2026-08-29 Apple M2 Max host. Attempts 01-04 retain
preflight, source and dependency acquisition boundaries; attempt 05 contains
the two successful clean-build receipts; attempt 06 retains a failed auditor
implementation; attempt 07 cross-binds that failure and contains the accepted
runtime, comparison, negative-control and verdict receipts.

The accepted comparison claim is **semantically identical, not byte-for-byte
reproducible**. The next active gate is `F0.2`.
