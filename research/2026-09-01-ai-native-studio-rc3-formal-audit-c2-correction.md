# RC3 formal audit C2 correction

Date: 2026-09-01

The frozen formal runner completed successfully with receipt
`c50e703b3469b3bda8324fe7e96f981dbb084da12f7eaea869f0d0fa0719eebe`.
The first independent auditor then raised `KeyError: 'resourceCeilings'` before
writing an audit result. The auditor incorrectly read inherited resource limits
from the v0.2 fixture-binding correction instead of the frozen v0.1 base. This
is an auditor defect, not a product or formal-run failure.

C2 leaves the completed formal evidence and workspace roots unchanged, performs
no Blender start or render, and writes only into a new audit root. It corrects
the inherited limit lookup and requires a new direct inspection of all formal
review media because the formal still files and one contact-sheet file were not
byte-identical to the development visual packet. Both complete formal videos
are byte-identical to the previously inspected videos, but that fact alone is
not used to bypass the new review.

No threshold, product source, solver result, final pose, event frame or rendered
artifact is changed.

The correction freeze is
`specs/ai-native-studio-rc3-physics-action-formal-audit-c2.v0.1.json` with self
hash `b8812bb769069242dcd9f75afea8cea9f59c2eb237808b254ce06bfb8cda1d42`.
