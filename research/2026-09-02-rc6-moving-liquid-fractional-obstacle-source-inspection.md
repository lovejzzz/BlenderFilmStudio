# RC6 moving-liquid fractional-obstacle source inspection

Date: 2026-09-02

Bound source: `lovejzzz/film-engine` commit
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`

The bound RNA describes `fractions_distance` as fluid/obstacle separation:
higher values hold fluid farther from obstacles; smaller values allow fluid
closer toward the obstacle interior. Its range is -5 to 5 and bound DNA default
is 0.5. In the generated liquid step, positive fractional distance is passed as
the threshold to `pushOutofObs` on every step when fractional obstacles are
enabled.

The current cup uses fractional obstacles, `surface_distance=2.0` cells and has
zero radial, floor or rim escape across all 24 frames, while reconstructed
volume still loses 17.05%. The next bounded test returns to exact attempt-65 and
changes only fractional obstacle distance 0.5→0.25. This is the single midpoint
toward zero, not a scan. The existing containment, one-body, manifold and volume
gates remain unchanged and will reject any gain achieved by obstacle intrusion.

Bound implementation hashes remain:

- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
