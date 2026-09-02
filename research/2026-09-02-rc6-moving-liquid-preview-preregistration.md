# RC6 moving-liquid Preview preregistration

Date: 2026-09-02

Status: preregistered before attempt-56 root creation

The accepted static-liquid control and C5F96 Bullet trajectory are now combined
for the first time. The question is intentionally smaller than a spill: can the
liquid remain coherent and move relative to the cup through frames 1–24, while
the exact solver-owned cup reaches at least 14 degrees?

The gate uses Preview resolution 96, one Data bake, one Mesh bake and no render
or save. It copies the accepted source `.blend` into a fresh root so its relative
cache path cannot target retained evidence, then binds the exact C5F96 transforms
for every frame. The larger motion domain has a 9.375 mm base voxel; mesh radius
2.5 preserves the accepted approximately 23.44 mm reconstruction context rather
than blindly carrying the local-domain number 4.5.

Every frame must have one positive liquid body, manifold reconstruction,
bounded source/temporal volume error, at most five percent outside the moving
cup plus one voxel, at most one percent below its floor and at least 2 mm of
cup-local centroid motion. The retained static cache must remain byte-exact.

This is still zero-render physics validation. A PASS permits a later, separately
frozen longer slow-tip stage; a FAIL is retained and diagnosed without tuning
the observed frame.
