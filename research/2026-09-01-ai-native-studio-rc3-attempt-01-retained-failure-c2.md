# RC3 development attempt-01 retained failure and C2

Attempt-01 stopped before any scene mutation. Both RC3 fixtures had been
self-hashed with ordinary Python JSON number spelling, while the product contract
uses the existing JavaScript-canonical number spelling. D1 therefore failed
`SELF_HASH_MISMATCH` before scene creation.

The frozen runner also trusted Blender's process exit code. Blender returned 0
despite the uncaught script exception, so the runner attempted to reopen a blend
that did not exist and then stopped. Two binary starts occurred; scene execution,
save, reopen, render, H1 and negative-control counts are all zero.

C2 does not touch product bytes. It creates D1 v0.3 and H1 v0.2 with only their
self-hash fields corrected using `film_studio_contract.javascript_canonical_json`.
A versioned runner uses fresh attempt-02 roots and now requires each declared
artifact immediately after its process, so a Blender exit-code false positive
cannot advance the sequence.
