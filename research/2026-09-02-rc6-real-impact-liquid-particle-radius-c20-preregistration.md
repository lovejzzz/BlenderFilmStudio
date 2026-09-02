# RC6 C20 preregistration — signed-error simulation particle radius

Date: 2026-09-02
Status: preregistered before attempt-93 root creation

C18 is a positive volume-gain failure and C19 shows that its smaller-amplitude
instability begins early in Data/Mesh. Blender RNA explicitly says to decrease
simulation `particle_radius` when a liquid gains volume. Mantaflow uses that
radius in particle level-set reconstruction and every resampling call.

C20 therefore changes exactly one value on C18: simulation particle radius
`1.8 → 1.6`. The value is the previously bounded slow-tip baseline, not a new
scan point. Fractions threshold remains0.10, CFL remains2, adaptive steps remain
2/8, Mesh particle radius remains2.5, and trajectory, geometry and all27 checks
remain unchanged.

Fresh attempt-93 permits one Blender start, one Bullet bake, one Data bake and
one Mesh bake under the existing2 GiB/64 MiB ceilings. It permits no render,
scene save, build, network call or engine mutation. Every outcome is retained.
A failure closes this direction; it does not authorize another radius, particle-
maximum change or Mesh compensation.
