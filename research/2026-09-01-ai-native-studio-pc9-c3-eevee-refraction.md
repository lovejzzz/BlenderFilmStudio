# PC9 C3 — native EEVEE refraction

PC9 development run-03 proves that selecting a Glass BSDF is not sufficient in the accepted product renderer. The bottles become nearly opaque and dark, hiding the exact fill-derived columns. Physics remains unchanged and passes, but direct visual questions 3 and 7 are NO.

The accepted binary exposes native EEVEE scene ray tracing and per-material screen/raytrace refraction. C3 preregisters only those native settings for the generic filled-bottle archetype. It does not authorize alpha tricks, a cutaway, an external fill gauge, label-based encoding, camera changes or any pose authoring.

The next development replay must make all three exact liquid heights readable while preserving the C1 physics result. Failure is retained and requires a new correction rather than threshold weakening.
