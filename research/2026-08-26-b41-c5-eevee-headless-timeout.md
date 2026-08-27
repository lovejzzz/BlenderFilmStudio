# B41-C5 · Eevee reaches render, then exceeds the 30-second success boundary

Verdict: `LINUX_AMD64_BLENDER_5_2_CANARY_FAILED`  
Image build: `PASS`  
Success canary: exit `143`, TERM at `30002 ms`  
Timeout canary: `FORCED_TIMEOUT_NON_PROMOTABLE`

## Measured progression

The corrected `BLENDER_EEVEE` identifier passed the C4 failure point. The success canary created its output-write probe and saved `canary.blend`:

- bytes: `95641`;
- SHA-256: `55112b7b7c878f7b751301e4d14d33706202538671caa681c856d63cad19ce3d`.

It produced no PNG or runtime report before the frozen 30-second wall-time. The runner sent TERM at `30002 ms`; Blender exited 143 at `30096 ms`, so no KILL was needed. stderr contained the already recorded missing `/work/tmp` PulseAudio warning and three `EGL_BAD_MATCH` messages. This proves the script reached the save-before-render boundary, but it does not distinguish a slow emulated Eevee initialization from a headless EGL dead end.

The image rebuilt successfully as `linux/amd64` with ID `sha256:c4b0f6bebe77e9bd10b4875aaf0500d798de081259397c525f923f7a9eea35b1`. The separate forced-timeout canary again reached READY, recorded TERM, received KILL after five seconds and exited 137 as non-promotable. Cleanup left zero experiment containers.

Independent audit matched tools and the observed partial artifact set and confirmed timeout non-promotion, but correctly failed the success claim.

## Next falsifiable boundary

The next step must be a separately preregistered diagnostic, not an unmeasured timeout increase. It should run the same saved-before-render canary under a small fixed wall-time ladder and record render-stage milestones, with headless software-render environment as an explicit controlled factor. Its purpose is to classify `SLOW_BUT_COMPLETES`, `HEADLESS_BACKEND_REQUIRED`, or `NO_COMPLETION_WITHIN_DIAGNOSTIC_CEILING`; it cannot itself promote the B41 worker contract.

Result SHA-256: `54f3a707498b958d4632b7f940be1e39c3f310b638ea5daa11afe53befcf258d`  
Audit SHA-256: `5a1212205a983bfaa9fa0e2ddb72b93a36ca9dc3c2e2829803d8a4e6de97c761`  
Success stderr SHA-256: `03a194d886ee49613d600c049fe951167915ac248dcd610cfcce2facd298d27a`

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-6/`.
