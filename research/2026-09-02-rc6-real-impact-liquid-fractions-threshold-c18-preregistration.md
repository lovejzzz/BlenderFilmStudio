# RC6 C18 preregistration — fractional-obstacle threshold

Date: 2026-09-02
Status: preregistered before attempt-90 root creation

C16 proved that lowering CFL alone is not a monotonic stability improvement: cup
intrusion improved, but particle support, liquid volume and fragmentation regressed
much earlier. C17 then located the new Data and Mesh expansion together at frame 24,
without a prior cup-intrusion breach.

C18 therefore returns to the exact C14 baseline and changes one different physical
degree of freedom: Mantaflow `fractions_threshold` from `0.05` to `0.10`.
This is the first exact UI step and is source-led by Blender's description and use of
the threshold during fractional-obstacle classification. CFL remains `2.0`, adaptive
steps remain `2/8`, and trajectory, geometry, particles, Mesh settings and all 27
acceptance checks remain unchanged.

Fresh attempt-90 permits exactly one Blender start, one Bullet bake, one Data bake
and one Mesh bake under the existing 2 GiB / 64 MiB roots. It permits no render,
scene save, build, network call or film-engine mutation. The result is retained
whether it passes, physically fails or exposes a harness failure. No second threshold
or compensating setting may be selected inside this experiment.

The executable contract is
`specs/ai-native-studio-rc6-real-impact-liquid-fractions-threshold-c18.v1.01.json`.
