# RC6 C26 attempt-104 — retained water-diffusion physical failure

Date: 2026-09-02
Status: immutable physical `FAIL 23/27`; original independent audit `FAIL 19/20`

C26 changed exactly one physical field on exact C18:
`use_diffusion false→true`. Blender's bundled Water values remained
`viscosity_base=1`, `viscosity_exponent=6`; `surface_tension` remained exactly
zero. APIC, particle2/8/16/radius1.8/band4, fractions0.10/0.25, CFL2,
timesteps2/8, Mesh, exact R40 Bullet motion and all27 gates stayed frozen.

The one Blender process completed one Bullet, all36 Preview-96 Data frames and
all36 Mesh frames in 1226.39 / 4.42 seconds. The exact cache roster is108.
There were zero renders, saves, builds, network calls or engine writes. Work
and evidence stayed near17.23 MB / 0.15 MB before final manifests, far below
their 2 GiB / 64 MiB ceilings.

## Physical result

The water-scale diffusion did not repair high-speed impact liquid:

- maximum source-relative volume error worsened `47.217227%→84.511311%`;
- maximum temporal drift worsened `33.451408%→67.281893%`;
- maximum positive bodies worsened `37→38`;
- maximum connected components worsened `37→38`;
- largest-component dominance worsened `71.584939%→63.982900%`;
- cup-solid intrusion remained under its gate but worsened
  `0.748564%→0.814978%`;
- significant spill moved from frame24 to frame34;
- temporal drift failed earlier, frame25→21; source-relative volume did not
  cross until frame36, positive bodies failed at frame34 and components at36.

The later visible spill together with earlier temporal failure is the useful
lesson: extra diffusion can make the motion appear less splashy while losing
the complete conservation result. Lower Data time (1404.51→1226.39 seconds)
does not override the physical regression. Close the diffusion flag and do not
scan viscosity or add surface tension.

## Retained audit defect

The independent audit recomputed all27 physical booleans exactly and passed
every provenance, process, cache, resource and no-render check. Its sole false
check is `claimCeilingExact`: the producer string says `exact C18, while` and
the frozen spec says `exact C18 while`. This one comma does not alter scope or
the physical result, but the original audit remains immutable `FAIL 19/20`.

A versioned C1 may perform one zero-Blender audit-only closure that accepts
only those two exact strings after proving the comma is their sole difference
and both retained roots remain byte-exact. It must not rerun Blender, rewrite
attempt-104 or change any physical interpretation. After C1, one copied-cache
C27 comparison is required before another Data-layer degree is selected.
Rendering remains forbidden.

## Evidence

- evidence root:
  `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104`
- work root:
  `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104`
- execution commit: `0a499332e8d2e3bb3b39db691236b4fce6eba159`
- result self hash:
  `8415bd595dc9fd7175b31a4a56cefaf5d9820c6b7d7af1f6f7eb3681a640a99c`
- receipt self hash:
  `0440e15a7063977395c23e4bebe92c4adae8c53adc3bb9d87f4babdc13a53ca7`
- original audit self hash:
  `1081a1c25da80abfffa01e57065623a06f137e5f684d929d5872af5c8bea11f3`
