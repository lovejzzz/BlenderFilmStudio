# B52-D12.7 · Adaptive local-risk gate holdout preflight

Date: 2026-08-27

Status: `ACCEPTED`

Preregistration commit: `22b0338aa2fcb168c4e94001bf9cbfe2d5a1e0f6`

Tool-freeze commit: `006d3934b3cf625e9f7e85bd837f0f5889d2be45`

Spec SHA-256: `c51d0d83afd30b479bf3e7109c31110133649ee3d65a04d677dbe236b8075ed0`

Preflight file SHA-256: `2e815621c41266da6db865ab5569901dbc19743b63f292629fa8018c36dd3dd8`

Preflight internal hash: `251052f3b7e3d9eb3630f110501098613cfe3706f88f515ab5ddfcd3ed8d80e6`

## Result

The frozen preflight passed 17/17 checks before the formal root existed. It bound all ten registered formal paths to their Git blobs, verified the Blender, Blender Python, Node and OCIO runtimes, and reproduced every D12.5-C2, D12.6-C2 and typed-envelope parent file/internal identity.

The Python and Node consumers independently processed one synthetic 117×79 fixture and produced byte-identical radius-2, radius-3, adaptive, boundary, rejected and float64 risk payloads. The synthetic fixture exercised both accepted and rejected adaptive pixels, both radius domains, the subset rules and the exact radius-2 partition. The inclusive equality/adjacent-float branch and 259 deterministic local-bound cases also passed.

Three separate real Blender 5.2.0 LTS processes then constructed every registered D12.7 geometry with zero render calls. The probes covered the dual-ripple grid, rounded box, superellipse prism, torus, UV sphere, cone frustum and cylinder crossbar, including their frozen three-frame static actions and required pass state. They emitted no EXR and no formal measurement.

Disk admission measured `107540692992` bytes available. After the frozen 24 MiB projection, `107515527168` bytes remained, only `141344768` bytes above the unchanged 100 GiB reserve. The formal runner must repeat this gate immediately before creating its fresh root.

## Boundary

This preflight validates executability, identities, arithmetic branch coverage and zero-render Blender scene construction. It does not reveal any D12.7 pixel, metric, gate or verdict. The three fixture outputs remain unseen until the single-use formal runner executes.

Artifact: `experiments/blender-static-adaptive-risk-gate-holdout-preflight-v0-1/frozen-tool-preflight.json`
