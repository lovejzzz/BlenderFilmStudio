# B62-T1-E1 · Terminal ScenePackageSpec → BuildPlan → Blender protocol

Date: 2026-08-29  
Status: PREREGISTERED — input ScenePackageSpec frozen; no T1 tool or formal root exists

## Why this is the next gate

B62 Phase 0 already provides a 288-frame, three-shot master with character, set, prop, performance, contact IK, core activation and animated lighting. D6 separately proved that the original close shot should be replaced by a 65 mm motion-aware camera baked across frames 193–288. The missing production bridge is not another camera search: it is a deterministic, auditable way to turn those exact admitted inputs into the scene that the terminal render will consume.

The existing general restricted SceneSpec compiler cannot honestly express this master. It only admits separately imported asset collections beneath `assets/` or `library/`, rejects embedded actions in those libraries, has no camera-cut routing, and has no generic material/light state animation contract. This experiment therefore freezes a deliberately narrow `bfs.b62TerminalScenePackageSpec.v0.1` dialect. It hash-pins a precompiled Phase 0 scene package and one admitted camera intervention. Passing it must not be advertised as general SceneSpec v0.6 support.

## Deterministic compilation

Two separate Node processes compile the exact input spec. Each verifies every Phase 0 and D6 parent file plus its internal self hash, then copies only D6 `frame`, `motionLocation` and `motionQuaternion` rows 193–288 into a canonical BuildPlan. Both plans must be byte-identical. The admitted plan contains its own SHA-256, the exact three-cut timeline and an explicit authorized delta: one camera object, one camera datablock, one seven-curve/96-key action, and rerouting only the existing close-shot marker.

All paths must be normalized repository-relative paths with no symlink or traversal escape. BuildPlan and formal evidence use exclusive creation. An existing formal root is a refusal, not a resume path in T1.

## Real Blender compile and independent reopen

The first fresh Blender 5.2 process starts with factory startup and auto-exec disabled, opens the exact Phase 0 master, checks runtime/source identity, applies only the BuildPlan delta and saves `B62_TERMINAL_PRODUCTION.blend`. It performs zero renders. The source master must retain its original SHA-256.

A second fresh Blender process opens only the derived scene and independently checks:

- frames 1–288 at 24 fps and the exact three timeline markers;
- wide and medium routing unchanged, close routing switched to the terminal camera;
- all 96 location/quaternion samples within `1e-6`, seven curves, 96 keys per curve and linear interpolation;
- exactly one added camera object, one camera data block and one action, with no deletion or mutation of existing IDs;
- Phase 0 asset identity, guardian performance, contact IK, core activation and light-state tracks preserved;
- Cycles CPU 64 spp, 1920×1080, 16-bit ZIP multilayer EXR, motion blur and pinned ACES-v2 color contract preserved;
- no render call and no model, network, Docker or Colima participation.

An independent Node auditor recomputes all identities, 20 gates and 12 semantic attacks. Mutation attacks operate on temporary in-memory or OS-temporary copies and must be refused before any native Blender spawn.

## Decision boundary

Only 20/20 gates and 12/12 rejected attacks support `B62_TERMINAL_SCENESPEC_BUILDPLAN_AND_SCENE_COMPILATION_SUPPORTED`. Any contract or preservation failure invalidates the run and leaves the scientific verdict null.

Success authorizes one separately preregistered, low-cost 288-frame animatic and full-timeline audit of the compiled scene. It does not yet authorize the expensive final Cycles sequence, claim restart safety for that render, or claim cinematic/photoreal quality.
