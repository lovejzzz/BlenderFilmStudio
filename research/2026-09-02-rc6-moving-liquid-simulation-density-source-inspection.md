# RC6 moving-liquid simulation-density source inspection

Date: 2026-09-02

Bound source: `lovejzzz/film-engine` commit
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`

The bound RNA defines `particle_number` as an integer factor from 1 to 5 where
higher values create more particles. The generated Mantaflow liquid script
uses that factor only as `discretization` when sampling the initial input level
set. During each liquid step, continuing particle density is controlled by
`adjustNumber(... minParticles, maxParticles, ...)`. Bound DNA defaults are
minimum 8 and maximum 16 particles per cell, and both RNA properties reset the
Data cache when changed.

Because the observed conservation defect develops across moving frames rather
than only at initialization, the next causal test targets ongoing reseeding:
change only `particle_min` from 8 to 12 while keeping `particle_max=16` and all
attempt-65 physics, Mesh and thresholds exact. Twelve is the single midpoint
between the bound default floor and ceiling. Initial `particle_number` remains
2. This is a one-value confirmation, not a scan.

Bound implementation hashes:

- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
