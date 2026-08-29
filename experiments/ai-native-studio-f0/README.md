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
