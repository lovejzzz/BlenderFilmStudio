# RC6 real-impact liquid timestep maximum C14 preregistration

Date: 2026-09-02

C13 proves that gross expansion already exists in Data support, beginning on
the same frame 23 as the Mesh failure. Bound source inspection selects one
high-speed stability variable: increase liquid `timesteps_max` from 4 to 8.

Attempt-86 must recreate exact C12 in one fresh root and change only that
single value. It retains the same R40 same-solve Bullet trajectory, frames
1–36, Preview-96 domain, APIC and particle settings, eight cup-effector
subframes, passive ramp, floor/ramp effectors, liquid source, Mesh settings and
all 27 physical thresholds. It performs at most one Blender start, one Bullet
bake, one Data bake and one Mesh bake, with zero render, save, native build,
network call or engine write.

The hypothesis is that allowing up to one fluid step per independently derived
effector sample prevents the frame-23 Data support expansion. A PASS requires
all original conservation, topology, spill, solid-exclusion, domain and causal
checks; improvement alone is not PASS. Every outcome is retained. No second
timestep value, CFL change, algorithm switch, surface tuning or render follows
without a new evidence-based gate.
