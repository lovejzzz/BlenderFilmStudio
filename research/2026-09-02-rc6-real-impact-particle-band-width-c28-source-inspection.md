# RC6 C28 source inspection — Particle band width

Date: 2026-09-02
Status: `PASS_READ_ONLY_SELECTION`

C28 performed no Blender start, bake, render, save, build, network call or
retained-root write. It inspected the exact RC5 source at
`8e18c82548f8716c415e6e1b69fdbbdeef1f1900` and the accepted C18 real-impact
configuration after C27 closed Water diffusion.

The next single falsifiable Data-layer change is
`particle_band_width: 4.0 -> 3.0` on exact C18. No second band-width value may
be selected after seeing the result.

## Source mechanism

Blender DNA defaults the property to `3.0`. RNA states that a larger value
creates a thicker particle band with more particles and invalidates the Data
cache. The generated liquid step passes the value to Mantaflow's continuing
`adjustNumber(... narrowBand=...)` resampling operation. The bound Mantaflow
implementation removes active particles deeper than the negative narrow-band
limit and only seeds replacement particles inside that limit. Reducing four to
three therefore narrows continuing particle preservation/reseeding by exactly
one base-grid cell; it is not merely an initial-distribution control.

Bound source file hashes:

- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
- `flip.cpp`: `83bc8bb4f4af7bbbeee88c3760c32dae687c80c1e2d1f7eb64a1169fa69dc332`

## Why this is the next test

C18 with band width `4.0` is the materially better real-impact baseline.
C27 showed that diffusion merely delayed positive expansion while early volume
loss and late expansion became worse. Particle radius, particle minimum and
maximum, fractional-obstacle controls, CFL/timesteps, diffusion, viscosity and
surface tension have already been tested or closed. APIC-to-FLIP would target
more splash rather than the measured support/conservation failure, and
deletion-based controls could hide evidence rather than repair physics.

Band width is distinct because it directly bounds ongoing FLIP-particle
support. A one-cell narrower band could reduce late particle/Mesh support
growth, but it could also worsen liquid loss. The unchanged 27 physical gates
must decide; later visible spill alone is not success.

The earlier slow-tip experiment moved this same property in the opposite
direction: `3.0 -> 4.0` reduced temporal Mesh-volume loss from `15.443%` to
`6.902%` and closed that bounded gate. C29 therefore tests regime sensitivity,
not a universal product default. If width `3.0` helps high-speed impact while
regressing the accepted slow-tip behavior, the software may not claim one
global value is correct; it would need a separately validated event/tier policy
or retain the existing setting.

## Frozen next step

C29 may run once in fresh bounded roots using the accepted RC5 binary. It must
copy exact C18, change only `particle_band_width` from `4.0` to `3.0`, preserve
APIC and all 27 physical/resource gates, and remain zero-render. It may not
perform a clean native build, scan another value, modify film-engine source or
reinterpret the slow-tip PASS.
