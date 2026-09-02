# RC6 slow-tip Bullet screen C1 preregistration

Date: 2026-09-02  
Status: preregistered before attempt-48 root creation

Attempt-47 is retained as a valid physical failure. Slowing the final
striker-to-ball-to-cup chain reduced the available tipping impulse; the four
cells peaked at only 7.25–14.67 degrees even though their derived Mantaflow
sampling requirement was only four or five subframes.

C1 does not lower the 45-degree response gate. It isolates the moving-container
lesson with a low-speed kinematic striker contacting the upper half of the cup
directly. The cup remains an unanimated active Bullet body and the ball has no
animation; for this control the ball is static and cannot mediate the result.

C1 also corrects a secondary measurement defect. A rotated cylinder's
transformed axis-aligned bound-box corners are not points on its surface and
can falsely extend below the floor. Attempt-48 measures every actual cup mesh
vertex for swept bounds, floor clearance and per-frame surface displacement.
The existing `-5 mm`, 45-degree, four-frame, one-voxel and ten-subframe limits
remain exact.

The run remains four Bullet-only starts with no Mantaflow, render, blend save,
native build, network call or engine write. Passing selects a causal trajectory;
it does not establish moving water or a finished shot.
