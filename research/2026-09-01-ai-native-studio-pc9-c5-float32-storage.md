# PC9 C5 — exact physical values across Blender storage

The C4 compatibility restoration passes exactly. The first PC9 reopen verifier then rejected two rigid-body masses because Blender stores that RNA field as float32: canonical decimal `0.30645` reopens as `0.30645001`, and `0.4811` as `0.48109999` when rounded to eight decimals.

This is a verifier-model error, not permission to add tolerance. C5 requires two independent exact representations: the canonical derived decimal must remain exact in the product result and object custom property, while `rigid_body.mass` must exactly equal the independently calculated IEEE-754 float32 representation of that same canonical value. Physics, COM, measured shutter, refraction flags and pose authority must remain exact.

No product source change is authorized by C5.
