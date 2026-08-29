# B62-T2-E1-C3 · Active production-scene render context

Date: 2026-08-29
Status: PREREGISTERED — v0.3 valid rejection retained; no C3 tool changed; v0.4 absent

v0.3 closes the diagnostic ambiguity: the complete renderer/auditor/video chain is technically valid, while the isolated Scene renderer produces 288 identical decoded frames. This is not a threshold edge case. It is a failure to bind frame/camera/animation evaluation to the render operator's active context.

C3 removes the isolated Scene. The exact loaded T1 production Scene becomes the active context Scene; Eevee and output properties change only in memory. Before every render the tool sets the exact frame, updates the active view layer, derives the latest frozen marker, assigns its camera, records context Scene/frame/marker/camera, and invokes `bpy.ops.render.render(write_still=True)` without a named-scene override. It never saves the `.blend` and must prove the source bytes remain unchanged after all 288 calls.

The retry root is `experiments/b62-terminal-animatic-continuity-v0-4`. It binds all three earlier roots, regenerates every frame, and retains all original acceptance thresholds, operation counts, resource ceilings and `HUMAN_PENDING` boundary.
