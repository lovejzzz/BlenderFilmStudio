# RC1-C1: bind environment and face roles before product mutation

RC1 v0.1 correctly froze the physical boundary, but its visual thresholds did
not identify which retained objects represent the chamber layers or the five
facial landmarks. A read-only product start on the unchanged source scene
confirmed four environment layers and five existing landmark meshes. It also
confirmed that the observation aperture and legacy eye parts are hidden in the
retained visual-failure scene.

C1 changes only the declarative fixture. It adds four environment roles and
five face-landmark roles, with all project object names confined to the
fixture. Product code must consume the roles uniformly. It may not branch on
the robot name, performance ID, fixture hash, or any bound object name.

No source scene, contact interval, spring parameter, acceptance threshold,
camera range, direct-review question, resource ceiling, authorized product
path, or final-pose rule changes. In particular, the existing armature may
continue to express intention, while Bullet alone owns spring displacement,
rebound, settling, and final mechanism pose.

This is a preregistration correction, not evidence of improvement.
