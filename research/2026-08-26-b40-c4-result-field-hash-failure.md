# B40-C4 · Runner pass rejected because result-only field was outside the evidence hash

Runner: `14/14 · replay PASS`  
Audit: `FAIL · IDENTITY_EVIDENCE_SELF_HASH`  
Status: `REJECTED_RESULT_FIELD_OUTSIDE_HASH`

B40-C4 fixed projection identity and produced the expected four blockers, 14/14 primary attack codes and stable pre/post-JSON replay. The independent audit matched the recorded attack vector exactly.

The runner added `replayPassed=true` only while assembling the final result object, after computing the evidence hash and attacks. The persisted result therefore contained a decision-relevant field not covered by `evidenceHash`. On reload, the audit recomputed the hash over the full result evidence and correctly rejected it.

Result SHA-256: `cb32e5beae35c9bb8d41ce9208936589c14f77748a7c5939cd1f665125bd61c7`  
Audit SHA-256: `ff2c91fd8cbef7e84a65eb39a55d8a7419e36d349709522a8f354832030792e7`

B40-C5 may change only field lifecycle: set `replayPassed=true` inside the evidence before self-hashing and attacks; if replay later fails, set it false and recompute the hash before writing. It may not add a duplicate result-only field.
