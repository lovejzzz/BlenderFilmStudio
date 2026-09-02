# RC6 C20 C1 attempt-94 — particle-radius impact result

Date: 2026-09-02
Status: retained physical FAIL 23/27; independent audit 20/21 pending audit-only precision closure

Attempt-94 completed the exact frozen 36-frame Preview-96 R40 Bullet/APIC
experiment after the interrupted attempt-93. The only physical change from C18
was simulation `particle_radius 1.8 → 1.6`. All 36 config, Data and Mesh files
were produced; the process took 1,568.62 seconds, including 1,553.60 seconds of
Data and 5.42 seconds of Mesh work. No render, `.blend` save, build, network
call or engine write occurred.

The physical result is a clear regression. Maximum source-relative volume error
rose from C18's 47.217% to 652.777%; temporal drift rose from 33.451% to
569.274%; positive bodies rose from 37 to121 and connected components from37
to122. Conservation first failed at frame24, positive-body count at25 and
component count at27, all earlier than C18. Cup-solid intrusion improved again,
from0.749% to0.286%, and all exact R40 trajectory, containment, floor, ramp,
domain, manifold, spill-opportunity and solver-authority checks remained true.
The result therefore passes23/27 but is not accepted liquid and must not be
rendered.

This falsifies a context-free reading of Blender's signed radius guidance. A
smaller simulation particle radius may be appropriate for generic volume gain,
but on this high-speed moving-obstacle impact it made the instability much more
severe and earlier. The product must learn the rule with physical context and
must reject the intervention when complete conservation/topology evidence
regresses; it cannot teach `decrease radius when gain` as an unconditional fix.

The independent audit recomputed all27 physical booleans exactly and passed20
of21 evidence checks. Its sole failure is `metricsRecomputed`: the producer's
unrounded centroid-shift value differs from a distance recomputed from published
eight-decimal sample coordinates by `1.017731782×10⁻⁸`, just above the frozen
`1×10⁻⁸` comparison. Three coordinates rounded to `1×10⁻⁸` imply a worst-case
distance error below `√3×10⁻⁸ ≈1.733×10⁻⁸`. A versioned audit-only C2 may use a
fixed `2×10⁻⁸` centroid replay tolerance while retaining `1×10⁻⁸` for the two
volume ratios. It may not rerun Blender, change a physical threshold or alter
either attempt root.

Result self hash: `63fbc90a79887af961d8d1e832734db5e0bb3367e3012004f549f8152d029620`.
Receipt self hash: `3e91c7db31d17d97160fde6c9ed564d012fbe19e28a89a3a989461c20c59a55f`.
Retained audit self hash: `676df66c969f5159b78686c02bab0a92c494e8eeb47c2a9af337d0c06128d801`.
