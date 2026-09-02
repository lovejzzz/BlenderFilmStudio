# RC6 C26 preregistration — one water-diffusion impact test

Date: 2026-09-02
Status: frozen before attempt-104 root creation

C25 selected one source-led change on exact C18: set `use_diffusion=true`
while leaving Blender's bundled Water viscosity values `base=1`, `exponent=6`
and `surface_tension=0` unchanged. Mantaflow applies the resulting `1e-6`
velocity diffusion before pressure and particle adjustment; the surface-tension
term remains exactly zero.

The exact question is whether this water-scale diffusion reduces the frame24
velocity-support amplification enough to improve the complete conservation and
topology result without changing the exact R40 Bullet path, spill opportunity,
containment or provenance.

Attempt-104 may use one Blender start, one Bullet bake, one Preview-96 Data
bake and one Mesh bake over frames1–36. It must preserve C18 APIC,
particle2/8/16/radius1.8/band4, fractional threshold0.10/distance0.25,
CFL2, timesteps2/8, all Mesh settings, the exact R40 trajectory and all27
physical checks. Workspace/evidence ceilings remain 2 GiB / 64 MiB with a
100 GiB reserve. Rendering, `.blend` save, build, network and engine mutation
counts are zero.

Run once in the unique fresh attempt-104 roots and retain PASS, physical FAIL
or harness failure. Do not try a second viscosity, add surface tension, change
solver method, tune another closed scalar, relax a gate or render after seeing
the result. A failing or incomplete physical gate requires one copied-cache
Data/Mesh comparison before another physical property is chosen.
