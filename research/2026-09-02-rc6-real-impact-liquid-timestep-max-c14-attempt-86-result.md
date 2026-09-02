# RC6 C14 attempt-86 retained result

Date: 2026-09-02  
Verdict: `FAIL_REAL_IMPACT_LIQUID_TIMESTEP_MAX_C14`  
Independent audit: `PASS` 20/20

## What changed

Exactly one liquid Data setting changed from the retained C12 configuration:
`timesteps_max` increased from 4 to 8. The R40 Bullet trajectory, APIC method,
geometry, domain, source, resolution, surface reconstruction and all 27 physical
acceptance checks remained frozen.

## What the experiment proved

The source-led change substantially reduced the catastrophic failure but did not
produce an acceptable liquid solve. Peak reconstructed volume fell from about
16.385 times source in C12 to 3.357 times source. Maximum positive bodies fell
from 239 to 50 and maximum connected components from 243 to 52. The largest
component remained at least 67.03% of positive volume, and the derived spill did
not begin until frame 31.

Five gates still failed: source-relative volume conservation, temporal volume
drift, positive-body count, connected-component count, and cup-solid intrusion.
Peak source-volume error was 235.70%, peak temporal drift 204.31%, and peak cup
intrusion 2.45%. The causal R40 Bullet path remained exact before and after the
fluid bake; domain, ramp and floor gates continued to pass.

This is a retained physical failure, not a rendered result. It shows that the
fluid timestep ceiling was a major contributor, but not the sole cause. Do not
repair, overwrite or render attempt-86. The next gate must inspect the fresh
per-frame transition and choose one further Data/collision variable; it must not
weaken thresholds or tune Mesh surface reconstruction.

## Evidence

- Evidence root: `experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86`
- Work root: `/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-liquid-timestep-max-c14-attempt-86`
- Freeze commit: `dcfa2b1bb355edccf218a4f7d6323c645362cf5f`
- Result hash: `5dbc4e416466567365e101d64f8c68b4d28323364f385a19cc9e451d115cabbf`
- Receipt hash: `c8d56e2b3ea85cc6a3c1bfdff304ef37d95546e5d056dd06f8b25a305409e5fc`
- Audit hash: `3c3dd1d592833811b4e5d24130492011ed9852d4c3480113d9acf0eb27047bbb`
- Counts: one Blender start, one Bullet bake, one Data bake, one Mesh bake;
  zero render, save, build, network call or engine write.

## Restart checkpoint

No Blender or bake process is running. Resume from this document and the
machine-readable current-state file. Begin with read-only analysis of the
attempt-86 transition; do not rerun C14.
