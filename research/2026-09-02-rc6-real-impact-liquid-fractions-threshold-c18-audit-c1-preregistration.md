# RC6 C18 C1 audit-only preregistration

Date: 2026-09-02
Status: preregistered before attempt-91 root creation

C18 attempt-90 completed the exact one-variable Bullet, Data and Mesh run and
produced a self-hashed physical FAIL. Its original independent audit recomputed
all 27 physical checks correctly and passed 19 of 20 evidence checks. The sole
false check compares two scope-equivalent but textually different claim strings:
the producer says “fractional-obstacle threshold … retained C14 baseline,” while
the preregistration says “fractions_threshold … exact C14.” The prohibited claims
and numerical scope are identical.

C1 changes only that audit comparison. It binds both exact strings and the two
exact substitutions needed to normalize them, hashes the complete immutable
attempt-90 work and evidence roots before and after, and writes only a new audit
under fresh attempt-91. It permits zero Blender starts, bakes, renders, saves,
network calls and retained-root writes. C18 remains a physical FAIL with 23/27
checks; this correction cannot promote it to a liquid pass.
