# RC6 moving-liquid solver minimum-timesteps preregistration

Date: 2026-09-02

Status: preregistered before attempt-63 root creation

Attempts 61 and 62 close moving-effector subframe tuning: subframes 2 cost
14.63% more Data time and slightly worsened both Data support and Mesh volume.
Attempt-63 therefore returns to the better attempt-59 baseline with 2.0-cell
surface distance and one effector subframe.

Exactly one different solver degree of freedom changes. Fluid-domain
`timesteps_min` increases from 1 to 2, forcing at least two simulation steps per
frame. Maximum timesteps remains 4 and CFL remains 2.0. The exact C5F96 Bullet
trajectory, Preview-96 tier, APIC, particle and Mesh settings, 24-frame window
and all source/temporal volume, topology, containment and resource thresholds
remain unchanged.

One Blender start, one Bullet bake, one Data bake and one Mesh bake are
permitted, with zero render, save, network or engine write. The result is
retained whether it passes or fails. No `timesteps_min=3`, CFL change, impact or
render may follow directly from the observed result.
