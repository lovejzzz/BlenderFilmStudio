# RC6 moving-liquid particle-band-width source inspection

Date: 2026-09-02

Bound source: `lovejzzz/film-engine` commit
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`

The bound DNA default for `particle_band_width` is `3.0`. RNA exposes the
setting from 0 to 1000, describes a higher value as producing a thicker
particle band with more particles, and resets the fluid Data cache when it
changes. The generated liquid step maps it to
`adjustedNarrowBandWidth_s$ID$` and supplies it only to the ongoing
`adjustNumber(... narrowBand=...)` particle-resampling call.

Attempt-68 is a clean near-pass: exact C5F96 motion, one positive manifold
body, zero radial/floor/rim intrusion and only 15.443274% temporal Mesh loss.
Attempt-69 independently shows that the fractional-distance improvement starts
in the Data cache. The next bounded run therefore preserves every attempt-68
setting and increases only `particle_band_width` from 3.0 to 4.0, one base-grid
cell. This tests whether a one-cell thicker resampling band retains enough
liquid support to close the remaining 0.443274 percentage-point gap.

This is not a scan. No second band-width value may be selected after seeing the
result. The existing source-relative/temporal volume, topology, manifold,
containment, trajectory, cache and resource gates remain unchanged.

Bound implementation hashes:

- `rna_fluid.cc`: `a2ca40cda63b5a6ab77a78d8ee14d039abbf0577f82c7f1904879fac777643d4`
- `DNA_fluid_types.h`: `356a47d3c8d1c0800ef72fa55bb2d1b1bde8112014cb8f625868276c8aeceead`
- `liquid_script.h`: `b526a55e9ba35d5ba41ef53dc5d027e9e13831a32a2862c424752b616a10392b`
