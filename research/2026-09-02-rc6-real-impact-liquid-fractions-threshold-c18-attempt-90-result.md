# RC6 C18 result — fractional-obstacle threshold

Date: 2026-09-02

C18 changed exactly one value on the C14 baseline: Mantaflow
`fractions_threshold 0.05 → 0.10`. CFL remained 2.0, adaptive steps remained
2/8, and the R40 trajectory, geometry, particles, Mesh settings and all 27
physical checks remained frozen.

The run is a retained physical `FAIL`, but it is a materially better failure.
It passes 23/27 checks instead of C14's 22/27. Maximum cup-solid intrusion
improves from 2.453988% to 0.748564% and now passes. Maximum source-relative
volume error improves from 235.700078% to 47.217227%; temporal drift improves
from 204.309821% to 33.451408%; positive bodies fall 50→37 and connected
components 52→37. The largest component also remains above the frozen half-
volume line at 71.58%.

Four checks still fail: source-relative conservation, temporal drift, positive-
body bound and connected-component bound. Therefore C18 is not accepted liquid
physics and must not be rendered. Data took 1404.51 seconds and Mesh 4.54
seconds; the exact R40 solve, domain, ramp, floor, manifold and provenance
checks remain valid.

The original independent audit passed 19/20 and failed only because the
producer wrote “fractional-obstacle threshold / retained C14 baseline” while
the preregistration wrote “fractions_threshold / exact C14.” C1 attempt-91
bound both exact strings, proved those two naming substitutions were the only
difference, re-hashed the complete immutable roots before and after, and passed
19/19 with audit hash
`2b1d988bf7aa2582b4ee02fdbeb74a4cf0e5e5077f7cdf7f42ca2a160d5625e8`.
The physical verdict remains FAIL.

Next, copy the immutable C18 cache into one fresh root and compare Data support
and Mesh transition timing against C14. Do not select another physical setting,
rebake, render or relax a threshold before that zero-Blender C19 diagnosis.
