# RC6 fluid iteration policy attempt-35 retained audit failure

The product validator passed nine positive cases and fifteen fail-closed
negative cases on the exact one-path product commit
`554539ed7db4de6b98358c6bdfd67943f4284cab`. The receipt self hash is
`2a971443ea448328b6caa7af199a96da5e0c55a0e8127759b87a55d1009f29bd`.
No Blender process, build, bake, render, network call or engine remote write
occurred.

The independent auditor is retained at `FAIL 14/15`. Its sole failed check is
`sourceTreesClean`: it checked the research worktree after the validator had
created the untracked formal evidence root, so it classified its own expected
output as source dirt. Product commit/path/module identity, committed research
bytes, receipt self hash, all recorded cases, independently recomputed tier and
cache decisions, FINAL admission, key attacks and zero-execution counts passed.
The retained audit self hash is
`6815b90cf793099d8fa94ead356e334db28cae237c115a9f37e9cdedbbaa774a`.

Attempt-35 is immutable. A C1 audit-only correction may run after these files
are committed and may change only research cleanliness evaluation: it must
verify the committed attempt-35 bytes and the clean product source tree without
replaying the product validator or changing its receipt. All scientific and
authority checks remain unchanged.
