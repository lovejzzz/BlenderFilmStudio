# Codex restart checkpoint — RC6 C12 tooling draft

Status at wrap-up: **SAFE TO RESTART CODEX**.

## Repository state

- Repository: `/Users/mengyingli/Documents/ChatGPT/MyBlenderFilmStudio`
- `HEAD`: `6e1c5552ba54b552039f2229746e2f7162b1b863`
- `origin/main`: `6e1c5552ba54b552039f2229746e2f7162b1b863`
- No Blender, bake, render, or `caffeinate` process is running.
- No C12 formal work or evidence root has been created.
- No Blender start, Bullet solve, Mantaflow bake, render, save, build, network call, or engine mutation was performed for C12.

## Uncommitted draft retained on disk

- Path: `scripts/run-rc6-real-impact-liquid-preview-c12-scene.py`
- SHA-256: `822d3ba10be0c459478007eff60ee3ee3d2a0587d9a27d91732830b35357a2a5`
- Lines: 439
- Adapter Python compilation: `PASS`
- Generated Blender-script compilation: `PASS` (670 lines)
- This is tooling preparation only. It has not been independently audited or run in Blender and must not yet be described as accepted.

## Frozen C12 intent

The next gate is `RC6-REAL-IMPACT-LIQUID-PREVIEW` C12 attempt-84: combine the retained R40 native Bullet trajectory with the accepted attempt-70 APIC Preview liquid configuration in one same-solve, frames 1–36 validation. The gate remains zero-render and zero-product-save. Its purpose is to test whether real impact causes measurable liquid spill and cup-local liquid displacement without deep solid intrusion or domain escape.

Planned unique roots remain absent:

- Work: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84`
- Evidence: `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-preview-c12-attempt-84`

## Resume sequence

1. Read `AGENTS.md`, `START_HERE.md`, and `handoff/ai-native-studio-current-state.v0.1.json`.
2. Read the `physical-film-direction` skill and its `validated-patterns.md` reference.
3. Run the read-only host preflight. Do not start a new native build while free space is below 160 GiB.
4. Review the retained C12 scene-adapter draft rather than recreating it.
5. Create and statically verify the standalone runner, independent auditor, v0.95 preregistration spec, and research note.
6. Commit and ordinary fast-forward push the frozen tooling/preregistration before creating the formal roots.
7. Run exactly one bounded C12 attempt under `caffeinate`; retain either scientific `PASS` or `FAIL` evidence unchanged.
8. Do not render screenshots or film until the C12 machine gate passes.

The prior accepted checkpoints and baselines remain authoritative; especially attempt-70 liquid, R40 from attempt-82, and C11 attempt-83. Do not modify retained evidence roots.
