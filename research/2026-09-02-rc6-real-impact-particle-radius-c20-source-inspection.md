# RC6 C20 source inspection — signed volume error selects simulation radius

Date: 2026-09-02

Blender RNA describes liquid `particle_radius` as a simulation particle radius
factor and gives a signed control rule: increase it when the simulation leaks
volume, decrease it when the simulation gains volume. This is distinct from
`mesh_particle_radius`, which controls final surface reconstruction and remains
frozen at 2.5.

The bound Mantaflow source passes `radiusFactor` into
`unionParticleLevelset` and every `adjustNumber` call. `adjustNumber` derives a
surface level-set threshold from the radius, kills particles outside the domain
or liquid, deletes excess particles away from the protected surface region and
seeds cells below the minimum. Lowering the radius narrows that protected
surface region; it is therefore a Data-layer intervention, not a cosmetic Mesh
change.

The accepted slow-tip baseline had negative temporal volume loss and improved
when radius 1.6→1.8. C18 has the opposite sign: reconstructed volume gains up to
47.22% above source. C20 therefore applies the source rule in the opposite
direction and tests exactly the previously bounded value 1.6 on the materially
better C18 baseline. It changes no other setting and retains all 27 checks.

This is not a radius scan. PASS, physical FAIL or harness failure closes the
one C20 value. No second radius, particle maximum change, Mesh tuning or render
may follow without retaining the result and a copied-cache diagnosis.
