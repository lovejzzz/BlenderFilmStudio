# PB.4 attempt-01 retained canonicalization failure

Status: **RETAINED HARNESS FAIL; product renders and independent pixel/pass audit PASS**

Attempt-01 consumed the preregistered single clean native arm64 build, four product starts and two render calls. The visible Render Job inspection, three pre-render negative controls, EEVEE preview, CPU Cycles multilayer EXR and the independent OpenImageIO audit all passed. The accepted PB.3 source remained byte-exact and the official Blender configuration remained unchanged.

The final Node.js wrapper rejected only `pixelPassAudit`. The Python auditor computed its self hash with Python JSON number spelling, retaining values such as `0.0`; the Node.js verifier reparsed the same value and serialized it as `0`. Python-native recomputation exactly reproduces audit hash `1dfc745926239d12ffa9bdd83f315979aba354f0ff93a5f006e2fb48a0ce5864`, while Node.js produces a different digest. This is a verifier canonicalization defect, not a pixel, pass, source, process or product-contract failure.

Retained bindings:

- Final FAIL receipt file SHA-256: `90cc68a66e991b99904a69c3dab97b8d7fe05ca094a43d621cd9f52b92a84378`; self hash: `dcf5b08606b6530f596a59abf230653d9444b11b3cfba1a7a701450854392afe`.
- Independent PASS audit file SHA-256: `622b4b659c55a720fa0650d062c1f650d5af038785c4637c9f04c965d1b3a62d`; Python-native self hash: `1dfc745926239d12ffa9bdd83f315979aba354f0ff93a5f006e2fb48a0ce5864`.
- Preview PNG SHA-256: `bcdaf54d543a6c7805024931f998ae910b635fa7c0b9789c3d6ab7b4a8d0c24e`.
- Final multilayer EXR SHA-256: `93955cfbf2abf885e04ac39a811f1e1e293275c3a968053085b40282458b6964`.
- Four process receipts are PASS; product render calls are exactly two; the independent auditor made zero render calls.

Attempt-01 is immutable. C1 may only create a fresh audit-only evidence root, verify the retained root byte-for-byte, reproduce the Python producer's declared canonicalization, and close the wrapper defect without rebuilding, restarting Blender or rerendering.
