# B52-D12.2 static Vector floor and three-layer evidence protocol

Date: 2026-08-27

Status: preregistered before formal tools or output

## Why this experiment exists

D12 produced two independent counterexamples to its original all-or-nothing contract. First, a visually immaterial static Vector residue (`1.5258789e-5 px` maximum) made an exact-zero reconstruction gate fail by `1.4901161e-7` RGB. Second, Python and Node produced byte-identical reconstruction arrays but disagreed on native JSON self-hashes. D12.1 removed JSON decimal spelling from document hashes, then showed that producer reductions over identical arrays can still differ by one ULP or approximately `5e-13 dB`.

The next claim must therefore not collapse three different questions into one boolean:

1. Are the machine payload arrays identical?
2. Can either runtime verify the same document bytes?
3. Do frozen decision metrics pass when recomputed independently from payloads?

## Fresh holdout

Three never-rendered static fixtures vary raster, lens, sensor width, object pose and camera pose. Frames 0, 1 and 2 use identical transforms, so no physical or authored motion exists. Each fixture is rendered twice from a fresh factory scene at both frame 0 and frame 1, giving twelve real Blender 5.2 Cycles source processes.

The registered tolerances are deliberately separated from exactness:

- maximum absolute Vector component: `1/4096 px`;
- maximum RGB reconstruction error: `1/524288`;
- RGB reconstruction RMSE: `1/1048576`;
- previous/current source beauty arrays: exact;
- repeat source arrays and reconstruction arrays: exact.

Whether every Vector/reconstruction error is zero is reported as an orthogonal observation. A nonzero residual falsifies exact-zero but does not itself reject the registered bounded production tolerance.

## Evidence architecture

Python and Node consumers receive the same immutable adapter arrays and emit no decision metrics. Their reconstructed RGBA and valid masks must match byte-for-byte. Each of the twelve producer reports is then encoded separately by both already-frozen D12.1 typed-envelope implementations; exact bytes and SHA-256 must agree per document.

A third Python analyzer does not import either consumer and ignores any producer metric field. It recomputes Vector and RGB measurements directly from adapter/payload arrays using a frozen scalar order. Thus payload agreement cannot be invalidated by JSON exponent style, and document agreement cannot conceal a different numeric reduction.

## Formal boundary and stopping rule

The formal run permits exactly 55 unique child processes: 12 Blender sources, 6 adapters, 12 consumers, 24 typed-envelope encoders and one analyzer. It permits zero model and network calls. The projected write is 32 MiB and admission requires at least 100 GiB free after projection.

The formal root is single-use. Any missing process, runtime mismatch, overwrite attempt, roster error, identity error or analyzer crash invalidates the run. It must be retained; a correction requires a new preregistration and a fresh output root.

## Non-claims

This is a narrow opaque rigid-planar static test. It does not establish moving history validity, deformation, transparency, disocclusion, complex ownership, perceptual quality or a universal Blender floating-point bound. The typed envelope remains a project-local binary64 normalization, not RFC 8785/JCS.
