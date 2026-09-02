# RC6 real-impact passive-ramp C9 attempt-81 result

Date: 2026-09-02

C9 is a retained physical `FAIL` with an independent 23/23 audit, but it
validates the missing causal mechanism. The ball has zero animation; the fixed
passive 0.30 m run / 0.06 m rise wedge alone redirected its Bullet trajectory.

- ball center at derived contact: 0.40016 m;
- contact: frame 20;
- first 5° response: frame 21;
- first 45° response: frame 33;
- peak cup tilt: 90.03°;
- floor gate: PASS;
- maximum cup-surface motion: 93.48 mm/frame;
- derived Preview-96 requirement: 10 subframes, FAIL;
- accepted-domain containment: FAIL, with swept max x=1.0163 m.

The ramp created a real contact moment and continuous solver response; its
60 mm rise was simply too strong for the frozen domain/cost gates. Preserve the
mechanism but not that amplitude. Do not start liquid or expand the domain.

The horizontal no-ramp attempt-77 and R60 now bracket the contact-height
transition. A future single-value C10 should keep I09, cup friction 0.75, 2 mm
margin and the 0.30 m ramp run, while reducing only rise to 0.04 m. That places
the predicted ball center at the frozen minimum raised-contact height 0.38 m
and ramp angle at 7.59°. This is a preregistration candidate, not a result.

Counts were one Blender start, one Bullet bake and zero liquid, render, save,
build, network and engine-write operations. Result/receipt/audit self hashes
are `413b2481...` / `3482e47c...` / `954136d8...`.
