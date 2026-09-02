# RC6 slow-tip Bullet screen C4 preregistration

Date: 2026-09-02
Status: preregistered before attempt-51 root creation

C3 proved that the explicit hinge has the correct axis and pivot geometry: at
90 degrees the evaluated cup center matched the rigid rotation around the
registered lower-right tangent. Its failure had two distinct causes. The
harness derived the cup-local pivot while the retained source was still
evaluated at frame 15, and the unlimited undamped hinge let gravity accelerate
the cup from the useful 45-degree passage to a 90-degree free fall.

C4 changes only those diagnosed causes. It frees the retained rigid cache and
evaluates frame 1 before deriving the local pivot, sets cup angular damping to
`0.8`, and enables a physical hinge range of `-60°/+5°`. Four slower direct
drives end at frames 28/32/36/40. Bullet still owns every cup transform; the
hinge has no motor and the cup and ball retain zero animation channels.

All C3 minimum-response, timing, floor, exact-surface, domain, sampling and
authority gates remain frozen. C4 adds one stronger condition: the mechanical
stop must keep peak cup tilt at or below 65 degrees. This remains a four-start,
zero-fluid, zero-render and zero-save screen. A PASS admits only the next
moving-liquid validation gate.
