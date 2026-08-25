# Research gaps and falsifiable experiment roadmap

Snapshot: 2026-08-25

## Why this record exists

The baseline establishes that Blender is a credible deterministic rendering backend and that many upstream AI-assisted components exist. The Blender 5.2 audit identifies the available control surfaces. The cost model explains where expenditure is avoided or shifted.

None of those records proves that the complete workflow can repeatedly produce an accepted cinematic shot at a lower total cost. The next research stage must therefore prioritize executable evidence rather than a broader capability catalog.

## Central finding

The project is missing five forms of evidence infrastructure:

1. A versioned definition of “cinema-grade” output and review conditions.
2. A formal SceneSpec contract that rejects invalid intent before Blender runs.
3. A representative benchmark suite rather than one favorable demonstration.
4. A validator calibrated against human review rather than a single image metric.
5. Raw telemetry for tokens, labor, rendering, failure, recovery, and accepted duration.

Until these exist, the project may claim technical plausibility but not end-to-end production readiness or economic superiority.

## Ten research gaps

| ID | Gap | Priority | Required artifact | Pass gate |
|---|---|---:|---|---|
| G01 | Cinema output target | P0 | OutputSpec v0.1 and controlled review environment | One EXR produces explainable, consistent results through two controlled display paths |
| G02 | Formal SceneSpec | P0 | JSON Schema contract and 20 valid/invalid fixtures | Invalid input is located before Blender launches; old schemas migrate or fail explicitly |
| G03 | Reproducibility boundary | P0 | Same-machine/cross-machine/version tolerance matrix | Structural hashes match exactly; pixels remain inside device-specific tolerance |
| G04 | Representative benchmark | P0 | Six fixed golden-shot packages | Every shot builds, fails, recovers, and produces a complete report |
| G05 | Automated acceptance | P0 | Validator plus human-review calibration | Required recall on a labeled failure set; machine/human disagreement is reported |
| G06 | Digital actor protocol | P1 | ActorSpec and layered performance contract | One identity survives close-up, full-body motion, and prop contact while remaining editable |
| G07 | Provenance and licensing | P1 | Asset manifest and provenance policy | Final pixels trace to shot, scene, asset version, license, and edit/generation history |
| G08 | Agent execution security | P0 | Restricted tool gateway and threat model | Adversarial tasks cannot escape paths, read secrets, access the network, or bypass approval |
| G09 | Recovery and editorial orchestration | P1 | Shot state machine and recovery drill | Random termination is recoverable; edit changes invalidate only required frames/dependencies |
| G10 | Comparative economics | P0 | Three-arm cost study and raw telemetry | Pre-registered comparison uses accepted seconds and identical acceptance criteria |

## BFS Benchmark v0.1

The first benchmark should contain six deliberately different shots:

1. **B01 — Material still life:** leather, metal, glass, skin-tone reference, and difficult highlights.
2. **B02 — Interior moving camera:** six-second dolly, window lighting, depth of field, and motion blur.
3. **B03 — Actor close-up:** dialogue, gaze, teeth, skin, and hair boundaries.
4. **B04 — Full-body contact:** walking, sitting, picking up and exchanging a prop.
5. **B05 — Secondary motion:** clothing, long hair, fast turn, collision, and cache invalidation.
6. **B06 — Large environment:** instancing, volume, reflection, far/near detail, VRAM pressure, and partial rebuild.

Every package contains:

- `scene.spec.json`
- `assets.lock`
- `golden.manifest`
- expected failure cases
- review reference
- `telemetry.jsonl`
- scene-linear `render.exr`
- human-readable report

## Four evidence layers

1. **Contract and structure:** schema validity, stable IDs, dependency closure, asset/license completeness, and structural hashes.
2. **Physical and technical:** penetration, contact distance, foot sliding, exposure, gamut, noise, missing frames, and EXR channels.
3. **Pixel and perceptual:** FLIP/HDR-FLIP, temporal flicker, identity descriptors, and reference composition differences. These are supporting signals, not definitions of cinematic quality.
4. **Human and economic:** blinded director review, first-pass acceptance, human minutes, token use, render hours, and cost per final accepted second.

No scalar metric is allowed to stand in for cinematography, performance, editing rhythm, or art direction.

## First 18-week falsification protocol

### Phase 0 — Freeze definitions (weeks 1–2)

Produce OutputSpec v0.1, SceneSpec v0.1, the failure taxonomy, and a pre-registered experiment plan. Do not begin automated content generation without a testable contract.

### Phase 1 — Prove determinism (weeks 3–6)

Build B01 and B02, the minimal compiler, manifests, validator, and cost telemetry. Two clean builds must be structurally reproducible. A lens or light edit must not invalidate unrelated dependencies.

### Phase 2 — Challenge the actor (weeks 7–12)

Build B03 and B04, ActorSpec, capture/retarget layers, and explicit contact events. The same actor must survive close-up and full-body contexts without neural-video finishing hiding failures.

### Phase 3 — Challenge scale (weeks 13–18)

Build B05 and B06, simulation-cache rules, crash recovery, and the three-arm economic comparison. Cost claims require raw records and accepted-second denominators.

## Immediate engineering action

Write SceneSpec v0.1 before building a complete user interface. Use B01 and B02 to create 20 valid/invalid fixtures. The compiler must validate before Blender starts, then emit a structural hash, scene-linear EXR, FLIP comparison, and complete cost log for two clean builds.

## Primary evidence

- [DCI Digital Cinema System Specification 1.5.0](https://www.dcimovies.com/dci-specification/)
- [ACES 2 Output Transforms](https://docs.acescentral.com/system-components/output-transforms/)
- [OpenEXR Technical Introduction](https://openexr.com/en/latest/TechnicalIntroduction.html)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [OpenUSD introduction and composition](https://openusd.org/release/intro.html)
- [VFX Reference Platform CY2026](https://vfxplatform.com/)
- [Blender Open Data Benchmark](https://opendata.blender.org/about/)
- [Blender 5.2 command-line rendering](https://docs.blender.org/manual/en/5.2/advanced/command_line/render.html)
- [NVIDIA FLIP](https://research.nvidia.com/sites/default/files/node/3260/FLIP_Paper.pdf)
- [C2PA 2.4](https://spec.c2pa.org/specifications/)
- [OpenTimelineIO timeline structure](https://opentimelineio.readthedocs.io/en/v0.17.0/tutorials/otio-timeline-structure.html)
- [Blender official MCP server warning](https://www.blender.org/lab/mcp-server/)

Negative results, disagreement, and uneconomic operating ranges are first-class research outputs.
