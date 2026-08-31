# PB.3 C6 attempt-04 retained pre-root failure

Date: 2026-08-31  
Verdict: **FAIL (harness authority plumbing; 0 Blender starts)**

The standing-authority execution contract was the sole path in commit `2cee2969bb3fcc7087c5f3bbcd9eface8cb8467d`. C6 successfully validated the active charter, owner delegation, single-path commit, exact roots, frozen tools, retained attempts and 13-input roster. The run then stopped before creating either formal root because the nested base runner performed a second historical execution-status check and emitted `PB.3 execution is not authorized`.

No Blender process, proposal, BuildPlan write, scene build, save, reopen, render, network call, engine edit or remote write occurred. The attempt-04 work root remains absent. The evidence root was created only afterward to retain `failure.json` and its independent 19/19 audit.

Failure file/self SHA-256: `3c805b9c3c19e71578ec7e5e26003433a11719a1fe8150ddf3b9b37cf3715525` / `79fc1fb6e1f6059bc7785c8d0c20d8fdfcbc56b49a40e43f14c391e47f7fcade`. Audit file/self SHA-256: `2050d027ab7c976733814b378853e123012dc8d9f1bf72d48970e63ce70bcf8b` / `74317f6429ab0fd64b9257f3d24915ae8c5e6a38686e223cfcd81d89f44faa55`.

C6-C1 permits one narrow correction: after the outer standing-authority validator passes, a closure-guarded adapter may satisfy only the nested base authority function with the already verified execution commit. All semantic, resource and artifact checks remain frozen. Attempt-04 is immutable; any later execution must use fresh attempt-05 roots.
