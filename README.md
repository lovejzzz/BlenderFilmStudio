# Blender Film Studio

Researching a reproducible **AI → structured 3D scene → Blender → cinema master** workflow.

**Published report:** https://lovejzzz.github.io/BlenderFilmStudio/

## Baseline 01

- Snapshot date: 2026-08-25
- Scope: 15 technical links from screenplay breakdown to neural finishing
- Standard: primary sources first; demonstrations are not treated as production readiness
- Core verdict: Blender rendering and scene control are mature; production-ready character creation, cinematic performance, complex contact, and general single-image world reconstruction are not yet end-to-end solved

The public report contains the full maturity matrix, current evidence, recommended architecture, and first experiment. A second research tab audits Blender 5.2 LTS across 18 film-production control domains. A third tab models production economics. A fourth converts the remaining unknowns into a falsification protocol. A fifth documents the executable OutputSpec and SceneSpec contract, including 22 passing accept/reject fixtures. A sixth records the first native Blender 5.2 compiler experiment with B01/B02 manifests and rendered preview evidence.

## Research records

- [`research/2026-08-25-baseline.md`](research/2026-08-25-baseline.md) — concise, reviewable snapshot
- [`research/2026-08-25-blender-5.2-intervention-map.md`](research/2026-08-25-blender-5.2-intervention-map.md) — Blender 5.2 control-surface audit
- [`research/2026-08-25-cost-model.md`](research/2026-08-25-cost-model.md) — subscription/API/rendering cost model and measurement schema
- [`research/2026-08-25-research-gaps-and-experiment-roadmap.md`](research/2026-08-25-research-gaps-and-experiment-roadmap.md) — prioritized gaps, benchmark suite, pass gates, and falsification plan
- [`research/2026-08-25-output-and-scene-spec-v0.1.md`](research/2026-08-25-output-and-scene-spec-v0.1.md) — executable output/scene contract and tested boundaries
- [`research/2026-08-26-compiler-v0.1-experiment.md`](research/2026-08-26-compiler-v0.1-experiment.md) — native Blender 5.2 B01/B02 structural experiment
- [`app/page.tsx`](app/page.tsx) — complete evidence-linked report content
- [`app/blender-5-2/page.tsx`](app/blender-5-2/page.tsx) — Blender 5.2 intervention tab
- [`app/cost-model/page.tsx`](app/cost-model/page.tsx) — production economics tab
- [`app/research-agenda/page.tsx`](app/research-agenda/page.tsx) — research agenda and experimental protocol
- [`app/spec-v0-1/page.tsx`](app/spec-v0-1/page.tsx) — human-readable specification tab
- [`app/compiler-v0-1/page.tsx`](app/compiler-v0-1/page.tsx) — executed compiler experiment and preview evidence
- [`specs/scene-spec.v0.1.schema.json`](specs/scene-spec.v0.1.schema.json) — executable JSON Schema contract
- [`specs/fixtures/scene-spec-fixtures.v0.1.json`](specs/fixtures/scene-spec-fixtures.v0.1.json) — 22 accept/reject fixtures
- [`specs/benchmarks`](specs/benchmarks) — B01/B02 benchmark SceneSpecs with pinned assets
- [`blender/compile_scene.py`](blender/compile_scene.py) — restricted Blender 5.2 compiler
- [`experiments/compiler-v0-1`](experiments/compiler-v0-1) — immutable BuildPlans, manifests, and result summary

## Local preview

Requires Node.js 22 or newer.

```bash
npm install
npm run dev
```

Run the executable contract tests with:

```bash
npm run validate:spec
npm run experiment:compiler
npm run render:compiler-previews
```

## Research policy

Each update should state its snapshot date, distinguish capability from reliability, link to primary evidence where possible, and record licensing or reproducibility constraints.
