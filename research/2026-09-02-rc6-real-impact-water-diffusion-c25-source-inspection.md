# RC6 C25 source inspection — activate the bound water-diffusion path

Date: 2026-09-02
Status: read-only source-led selection; zero Blender starts and zero scene mutation

Bound product source is `lovejzzz/film-engine` at RC5 commit
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900`. C24 accepted that lowering the
per-cell particle ceiling `16→12` produces a mixed cache response but makes the
complete C23 physical result worse. Radius, CFL, fractional-obstacle threshold,
particle minimum/maximum and their tested values are closed.

## What the source proves

The C18-derived impact builder does not assign `use_diffusion`,
`surface_tension`, `viscosity_base` or `viscosity_exponent`. The bound DNA
defaults therefore control them:

- the domain flags do **not** include `FLUID_DOMAIN_USE_DIFFUSION`;
- `surface_tension = 0.0`;
- `viscosity_base = 1.0` and `viscosity_exponent = 6`.

Those last two values exactly match Blender's bundled `Water.py` fluid preset.
Mantaflow converts them to `1 × 10^-6`, divides by squared domain size, then
forms `alphaV = kinViscosity * timestep * resolution²`. When and only when
`use_diffusion` is true, `cgSolveDiffusion` applies that value to the liquid
velocity grid before curvature calculation, wall-boundary enforcement and the
pressure solve. This is a direct Data-layer velocity intervention before the
same pressure/particle-adjustment path implicated by C18/C24.

Surface tension is deliberately **not** selected. A nonzero tension value alone
does not allocate the curvature grid because that allocation is gated by
`use_diffusion`. Turning diffusion on while also changing tension would alter
two physical effects. With the selected change, tension remains exactly zero,
so `surfTensHelper` contributes exactly zero even though the curvature grid is
available.

Other source-visible candidates are rejected for this gate:

- `particle_number` and `particle_randomness` affect initial level-set sampling,
  not the continuing `adjustNumber` transition; raising number 2→3 would also
  raise three-dimensional sampling candidates from 8 to 27 per eligible cell
  before the unchanged maximum-16 reseed logic.
- `simulation_method=FLIP` activates the existing `flip_ratio=0.97`; Blender
  describes FLIP as more splashy and APIC as more energetic and stable. That is
  not the narrow, source-signed repair for the current fragmentation failure.
- `sys_particle_maximum` and `delete_in_obstacle` can discard material and would
  risk hiding the measured failure rather than correcting the solve.
- `flip_ratio` is inactive on the frozen APIC path.

## One selected C26 change

Return to exact C18 and change only:

`use_diffusion: false → true`

Keep `viscosity_base=1.0`, `viscosity_exponent=6`, `surface_tension=0.0`, APIC,
particle radius1.8, minimum/maximum8/16, band width4, fractional distance0.25,
fractional threshold0.10, CFL2, timesteps2/8, Mesh settings, exact R40 Bullet
motion and all27 physical gates unchanged.

The falsifiable hypothesis is that Blender's bundled water-scale velocity
diffusion reduces the frame24 velocity-support amplification enough to improve
the complete conservation/topology result. It may instead be too weak, add
cost or change no failing gate. C26 must run exactly once in fresh bounded
roots, retain every result and remain zero-render. No second viscosity value,
surface tension value, solver-method change or threshold relaxation may follow
from looking at the result; compare copied Data/Mesh onset before choosing any
later degree of freedom.

## Bound implementation hashes

- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `MANTA_main.cpp`: `aa06317e5038ddaa376d8807db705ec4ffc45b56c660c1e2eefa42b8b82618ff`
- `fluid_script.h`: `b8c1fce0ba31e506e01c1133f267175511216608c1fde1f32bdd81db126e16d8`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
- Mantaflow `pressure.cpp`: `0807ae0fe9d73d1ff76d1c1d17892f49f6b9ddf8f62f1724d53e4548a1b46453`
- Mantaflow `flip.cpp`: `83bc8bb4f4af7bbbeee88c3760c32dae687c80c1e2d1f7eb64a1169fa69dc332`
- Mantaflow `apic.cpp`: `f83a5f9eb1201c29c1a2095eb50cdd852bc1e06dfb59da5909887002c2831069`
- bundled `Water.py`: `3eea321f62edc4aad02855cdb4e936d156c1f15415858f9466b2f91395360118`
