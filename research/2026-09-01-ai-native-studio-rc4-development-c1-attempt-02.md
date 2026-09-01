# RC4 development C1 / attempt-02

RC4 development attempt-01 stopped before scene mutation. The accepted binary
preloaded its installed `film_studio_physics_action` module during startup, so
the development product tool's path insertion did not select the candidate
module. The installed RC3 module correctly rejected the new
`SETTLED_GROUP_RESPONSE` beat. Blender reported process exit `0` despite the
Python traceback; the harness then stopped because the required blend was
absent.

The retained failure is immutable at
`experiments/unstaged-physical-realism/RC4-2026-09-01-development-attempt-01`.
There were no scene mutations, saves, renders, network calls or product remote
writes.

C1 changes only module resolution in the external development tool: remove the
two candidate module names from `sys.modules`, prepend the frozen candidate
module root, import again, and assert the resolved source path before
inspection. The RC4 fixture, product patch, physical thresholds, visual
questions and resource/count ceilings do not change. Attempt-02 uses fresh
work and evidence roots frozen in
`specs/ai-native-studio-rc4-development-c1-attempt-02.v0.1.json`.
