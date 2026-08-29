# B62-T2 v0.3 · Complete technical run, valid frozen-pixel rejection

Date: 2026-08-29
Verdict: `B62_TERMINAL_288_FRAME_ANIMATIC_OR_CONTINUITY_REJECTED`
Evidence root: `experiments/b62-terminal-animatic-continuity-v0-3`

## Outcome

The complete T2 control plane works: 288 Eevee calls, exact PNG roster, a second fresh Blender reopening the T1 source, all 96 close-frame geometry measurements, causal-state checks, FFmpeg encoding, ffprobe metadata and self-hashed Node audit all completed within budget. Twelve of fourteen gates pass. The valid scientific failures are G07 temporal non-freeze and G08 cut-pair difference.

Every PNG is finite, dynamic and nonempty, but all 288 decoded pixel arrays are identical. Each shot has one distinct decoded digest, the whole sequence has one, and both cut pairs are equal. FFmpeg independently reproduces one raw-frame MD5 across all 288 frames. The MP4 is therefore a 12-second carrier of one frozen image, not an animatic.

The independent source-scene audit still proves all 96 close frames satisfy the unchanged D6 geometry template and that contact/core/warm-light causal state is correct. This separates a valid production Scene from a broken render-context application.

## Root cause and boundary

The renderer created and advanced a separate Scene, then invoked `bpy.ops.render.render(scene=name)`. Blender rendered that named Scene but consumed evaluation from the active context, which remained at the initial wide state. Correct pre-render marker/camera labels in a report were therefore insufficient; actual decoded pixels exposed the mismatch.

v0.3 remains a valid scientific rejection. C3 is a newly preregistered renderer intervention: render the exact loaded production Scene as the active context Scene, mutate only in-memory render/frame/camera state, never save it, and require the source file hash to remain exact.

No threshold is relaxed, and no v0.3 output may enter the retry.
