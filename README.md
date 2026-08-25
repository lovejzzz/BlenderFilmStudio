# Blender Film Studio

Researching a reproducible **AI → structured 3D scene → Blender → cinema master** workflow.

**Published report:** https://lovejzzz.github.io/BlenderFilmStudio/

## Baseline 01

- Snapshot date: 2026-08-25
- Scope: 15 technical links from screenplay breakdown to neural finishing
- Standard: primary sources first; demonstrations are not treated as production readiness
- Core verdict: Blender rendering and scene control are mature; production-ready character creation, cinematic performance, complex contact, and general single-image world reconstruction are not yet end-to-end solved

The public report contains the full maturity matrix, current evidence, recommended architecture, and first experiment. A second research tab audits Blender 5.2 LTS across 18 film-production control domains. A third tab models the economics of a subscription-first Codex CLI + Blender workflow, including API, rendering, hardware, assets, labor, and rework.

## Research records

- [`research/2026-08-25-baseline.md`](research/2026-08-25-baseline.md) — concise, reviewable snapshot
- [`research/2026-08-25-blender-5.2-intervention-map.md`](research/2026-08-25-blender-5.2-intervention-map.md) — Blender 5.2 control-surface audit
- [`research/2026-08-25-cost-model.md`](research/2026-08-25-cost-model.md) — subscription/API/rendering cost model and measurement schema
- [`app/page.tsx`](app/page.tsx) — complete evidence-linked report content
- [`app/blender-5-2/page.tsx`](app/blender-5-2/page.tsx) — Blender 5.2 intervention tab
- [`app/cost-model/page.tsx`](app/cost-model/page.tsx) — production economics tab

## Local preview

Requires Node.js 22 or newer.

```bash
npm install
npm run dev
```

## Research policy

Each update should state its snapshot date, distinguish capability from reliability, link to primary evidence where possible, and record licensing or reproducibility constraints.
