# B62-Q1-D1-C1 version normalization correction

The first D1 formal root is retained as invalidated. Both fresh Blender processes exited zero, each reported zero renders, and each wrote the full three-shot observation. The independent Node auditor then exited one before comparing geometry because it compared `bpy.app.version_string` (`5.2.0 LTS`) directly with the preregistered CLI identity (`Blender 5.2.0 LTS`). The build hash was the expected `fbe6228777e7` in both documents.

This is a contract-normalization error, not evidence for or against the geometric hypothesis. C1 permits only two Node changes: the auditor adds the literal `Blender ` prefix before the exact version comparison, and the runner binds C1 plus the immutable v0.1 tree before using a fresh v0.2 root. Both Blender tools remain byte-for-byte frozen. The grid, shots, anchors, diagnostic thresholds, process counts, zero-render boundary and budgets remain unchanged.

The v0.1 retained tree is 7 files, 1,527,639 bytes, SHA-256 `bbd777378b268958d914a4512a4dc94cca471c698c2d943dc3714223c24201ce`. Its two observations may not be copied into v0.2 and were not consulted to alter the hypothesis.

Machine-readable correction: `specs/b62-camera-quality-c1-version-normalization.v0.1.json`.
