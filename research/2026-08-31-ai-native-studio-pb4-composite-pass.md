# PB.4 preview, final and receipts — composite PASS

PB.4 is closed `PASS` by two immutable evidence roots.

Attempt-01 contains the real product result: one clean native arm64 build from engine source commit `df5c296789a8d57cd84f4f8fb586bb28243f3fa5`; one visible Render Job inspection with typed-state save/reopen; three pre-render failure controls; one 640×360 EEVEE preview; one 640×360 CPU Cycles multilayer EXR with Combined, Depth and Normal; four PASS process receipts; process, stage, failure and cost receipts; and an independent OpenImageIO audit whose source, process, pixel, pass and failure checks are all true.

Attempt-01 remains a retained wrapper `FAIL`. Its sole false final check is `pixelPassAudit`, caused by cross-runtime JSON number spelling (`0.0` in the Python producer versus `0` after Node parse/reserialize). The wrapper receipt is not rewritten.

C1 attempt-02 is an audit-only correction. It binds all 28 attempt-01 files at full-root manifest SHA-256 `8fcc9535670f02b3d553a6c41b78cd4bf6c4f3af7a082f97c275648360c238d8`, reproduces the Python producer's declared canonicalization, and independently verifies the retained receipts, eight logs, three failure controls, two artifact hashes, source, binary, cost and resource bounds. It passes 25/25 with audit hash `65e952665943b7545b8fced7d86cdd4bbf5e3a29c7b7ffe2fd5dfd5b2d23cd1b` and receipt hash `687f2759637b45e5354264283fcc4b8e7539394ae773b8c74a14c6211356078a`. It performed zero builds, Blender starts, renders, source mutations, engine remote writes or network calls.

Accepted artifact bindings:

- Preview PNG: `bcdaf54d543a6c7805024931f998ae910b635fa7c0b9789c3d6ab7b4a8d0c24e`.
- Final multilayer EXR: `93955cfbf2abf885e04ac39a811f1e1e293275c3a968053085b40282458b6964`.
- Product binary: `54810b426d73cf6649c0f5c9b5c763b2ce59e7f1c0a2f6245bc065b906fda636`.
- Accepted PB.3 B01 source remains `64026648bde5f6128e2642797a8c8a4aa867286f20c633c80717a7093b1c012b`.

Claim ceiling: this proves one frozen B01 preview/final path and receipts on one admitted arm64 host. It does not establish public binary distribution, production readiness, cross-platform support or autonomous filmmaking. The next gate is PB.5 restart-safe job control.

After composite acceptance, the validated engine commit was published to `lovejzzz/film-engine` by one ordinary fast-forward of `main` from `4061e12bd45a2bec83e68d0cf49abbf56d4738f6` to `df5c296789a8d57cd84f4f8fb586bb28243f3fa5`. A read-only remote query and non-browser raw-file checks verified the OID and all three source hashes. No force push, other ref, tag, release, LFS upload or binary distribution was performed.
