# RC6 typed fluid iteration policy accepted

The one-path product candidate
`554539ed7db4de6b98358c6bdfd67943f4284cab` adds the pure-Python module
`scripts/modules/film_studio_fluid_pipeline.py` on exact public baseline
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900`. The module has no `bpy`
dependency and cannot start a bake or render.

Formal attempt-35 passed nine positive cases and fifteen fail-closed attacks.
It derives the four frozen tiers—DRAFT 64, PREVIEW 96, REVIEW 128 and FINAL
192—from product authority rather than accepting a caller resolution. Typed
physics, surface and visual state hashes select exactly one of:

- `BAKE_DATA_THEN_MESH` for initial state, tier/resolution changes or any
  physical-state change;
- `REUSE_DATA_BAKE_MESH` for a surface-only change with an exact Data cache;
- `REUSE_DATA_AND_MESH_VISUAL_ONLY` for a visual-only change with exact Data
  and Mesh caches;
- `REUSE_ALL` for an exact state.

FINAL always changes resolution and therefore starts a new Data plus Mesh
stage. It rejects before work unless a self-hashed REVIEW receipt binds the
same non-resolution physical identity, surface identity and frame window, plus
external machine-audit and visual-review hashes.

The base independent audit is retained at 14/15 because it queried research
cleanliness after the validator had created its own untracked evidence root.
Audit-only C1 corrected only that timing, bound the immutable base failure and
passed 16/16 with self hash
`01c53e8e18667996a9a2d7d75044d9a6fe861f2caecc01aed318ebc9199465b5`.
The retained product receipt self hash is
`2a971443ea448328b6caa7af199a96da5e0c55a0e8127759b87a55d1009f29bd`.

This accepts the pure decision policy only. It does not yet prove Blender UI
integration, actual cache execution, runtime speedup, corrected liquid
physics, slow-tip behavior, impact or finished-film quality.
