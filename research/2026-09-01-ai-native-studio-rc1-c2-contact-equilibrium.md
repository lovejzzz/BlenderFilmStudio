# RC1-C2: separate anchor, contact, and spring equilibrium

The first unsaved development execution produced real Bullet motion but exposed
two measurement errors in RC1 v0.1. The closest inward effector-to-support
sample is frame 179, while the finite-size hand collider begins moving the
finite-size plunger earlier. Separately, the Generic Spring constraint has a
stable precontact Bullet equilibrium 12.33727 mm from the authored object
origin. Measuring residual motion from the object origin therefore reports a
false non-settle even when the solver returns exactly to its own equilibrium.

C2 does not move the contact path, spring, collider, camera, or final pose. It
names the closest sample the anchor frame, derives the contact frame from the
first solver response, and measures peak/reversal/settling relative to an
eight-frame precontact Bullet equilibrium. The impact presentation and native
shutter measurement use the solver-selected peak response frame.

All original 25–50 mm peak, two-frame response, reversal, 2 mm / eight-frame
settle, zero mechanism-pose-keyframe, visual, resource, and authority floors
remain unchanged. No formal root, saved scene, or product commit existed when
this correction was frozen.
