# RC6 C26 C2 preregistration — exact two-log-path correction

Date: 2026-09-02
Status: frozen before attempt-106 evidence-root creation

C1 stopped before root creation because its generated audit retained exactly two
C18 log paths. C2 preserves the frozen C1 tool and spec, requires attempt-105
to remain absent, and changes only:

- `01-real-impact-fractions-threshold.stdout.log` →
  `01-real-impact-water-diffusion.stdout.log`
- `01-real-impact-fractions-threshold.stderr.log` →
  `01-real-impact-water-diffusion.stderr.log`

The one-comma normalization, immutable attempt-104 root manifests, exact
physical metrics and all zero-Blender ceilings remain unchanged. C2 may create
only fresh audit-only attempt-106. A pass closes the harness defect but leaves
C26 at physical `FAIL 23/27`; the next physical work is still prohibited until
a copied-cache C27 comparison is frozen and completed.
