# RC6 C20 C2 preregistration — audit-only centroid replay precision

Date: 2026-09-02
Status: preregistered before attempt-95 evidence-root creation

C20 C1 attempt-94 is an immutable physical FAIL23/27. Its original independent
audit passes20/21 and recomputes every physical boolean exactly. The sole failed
evidence check compares an unrounded producer centroid distance with a replay
from published coordinates rounded to eight decimal places. The observed delta
is `1.017731782×10⁻⁸ m`.

For a displacement vector derived from two three-axis points, rounding each
coordinate to `1×10⁻⁸ m` bounds the distance replay error by `√3×10⁻⁸ m`.
C2 therefore changes exactly one auditor literal: centroid replay tolerance
`1×10⁻⁸ → 2×10⁻⁸ m`. The two volume-ratio replays remain at `1×10⁻⁸`; all27
physical checks, every threshold, source/result/receipt byte, root and claim
remain unchanged.

One system-Python audit process may create only the fresh attempt-95 evidence
root. Blender, Bullet, Data, Mesh, render, save, build, network and engine-write
counts are all zero. The tool must re-execute the complete C1 independent audit
logic against retained bytes, independently bind C1 and C2 freeze commits, and
verify the retained work/evidence manifests. Any other failure remains a failure.
