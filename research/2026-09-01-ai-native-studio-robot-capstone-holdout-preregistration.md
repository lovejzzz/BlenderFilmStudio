# RC1 — robot capstone as a physical-performance holdout

PC9 is accepted and published, so the retained robot may now be used as a holdout rather than a hand-tuned fixture. Direct inspection of PC4-VX2 confirms the prior visual failures and a deeper physical gap: the file contains 183 objects, one 18-bone guardian rig, 32 guardian animation curves and a working right-hand IK constraint, but zero rigid bodies and zero rigid-body constraints. The contact performance is entirely authored animation.

RC1 draws a strict boundary. Existing skeletal animation may express the robot's intention and drive one kinematic hand collider. The software must derive the contact frame and mechanism anchor from the evaluated hand trajectory and console surface. A spring-loaded control then compresses, reverses and settles through Blender Bullet; its response and final pose have no authored keyframes.

The visual contract also closes the known false pass: medium occupancy is bidirectional, environment layers must remain visible, and at least four facial landmarks must be readable without a dominant side pod. Product code may consume declarative semantic bindings but may not branch on this project's names, ID or hash.

This document preregisters the holdout before any robot product or scene mutation. It does not claim a result yet.
