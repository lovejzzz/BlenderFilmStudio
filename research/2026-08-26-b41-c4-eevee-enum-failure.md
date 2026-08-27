# B41-C4 · Real amd64 Blender launch; Eevee enum mismatch

Verdict: `LINUX_AMD64_BLENDER_5_2_CANARY_FAILED`  
Image build: `PASS`  
Timeout canary: `FORCED_TIMEOUT_NON_PROMOTABLE`  
Success canary: exit `1`

## First real Linux worker evidence

Guest buildx completed in `117808 ms`. Docker independently inspected the loaded image as:

- image ID: `sha256:0ca8ce490080dd0ef4b23fda0f70c517700873d163de470fa102310df521941b`;
- OS/architecture: `linux/amd64`;
- Docker-reported content size: `1004901200` bytes.

The success container launched the official Linux binary under the frozen non-root, read-only-root, no-network and cgroup contract. Its stdout identified `Blender 5.2.0 LTS`, build `fbe6228777e7`, and the frozen OCIO path. The process reached the mounted Python canary and created the writable-output probe.

It then failed at `scene.render.engine = "BLENDER_EEVEE_NEXT"`. This Blender 5.2.0 runtime exposed the exact enum set `('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')`; `BLENDER_EEVEE_NEXT` is not valid. The exit was `1` after `14465 ms`; no runtime report, PNG or `.blend` was produced. This is a canary API defect, not a renderer or container-start failure.

The runtime also emitted a nonfatal PulseAudio warning because `/work/tmp` did not exist even though `/work` itself was a writable tmpfs. This warning is recorded but is not the observed cause of exit. It is not bundled into the next one-variable correction.

## Timeout gate

The separate timeout canary reached `READY`. At `30002 ms` the runner sent TERM; the script recorded SIGTERM. At `35023 ms` the runner sent KILL. Docker returned exit `137`, both observations existed, and the receipt remained non-promotable. No experiment container remained running.

Independent audit matched all current tools and artifact absence and confirmed timeout non-promotion, but correctly failed because the success canary failed.

B41-C5 may change only the Eevee engine identifier and the corresponding analyzer projection/actual-runtime check. Every other launch, isolation, render, timeout and identity condition remains frozen.

Result SHA-256: `3cc14c978d7c21e9abd48a9608b8f39b03be665e0f24fab2e014fa834a114523`  
Audit SHA-256: `e7ba1b22ffd79c6dd38d89d05fc305b3184c6f713557aaeb25a93d684585e87e`  
Success stderr SHA-256: `9087e14f22e0a342cf1c3949a96aff049a719ff71c58ec37c64adf51c7bf817d`

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-5/`.
