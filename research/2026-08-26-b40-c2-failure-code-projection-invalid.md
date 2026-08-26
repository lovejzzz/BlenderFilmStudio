# B40-C2 · Serialization-stable evidence rejected by failure-code projection

Base analysis: `PASS`  
JSON round-trip: `PASS`  
Attacks by preregistered primary code: `0/14`  
Status: `INVALID_FAILURE_CODE_PROJECTION`

B40-C2 successfully removed cross-tree aliases. Base analysis, capacity decision, evidence hash and the complete observed attack vector were identical before and after JSON round-trip. The four capacity blockers remained unchanged.

However, the C2 wrapper converted every failed base analysis into the single wrapper code `BASE_ANALYSIS` and did not append the base analyzer's specific codes. Each mutated candidate was rejected, but none exposed its preregistered primary code such as `POLICY_IDENTITY`, `CAPACITY_DECISION` or `EMULATOR_REGISTRATION`. Therefore every attack's `passed` field was false and the runner verdict remained `SERIALIZATION_STABILITY_FAILED`.

The independent audit reproduced `roundTrip=PASS` and `attacks=0/14`, then correctly failed.

Result SHA-256: `b7f20549d49ac2dd4fb12693a2f37308d945d6b60b53389f5a9cdc582d75682d`  
Audit SHA-256: `9e0da26bf645c8dc83246b1f7488ef51c10a8fd664530d411ae94492b23a0b9c`

B40-C3 may change only failure-code projection: append the ordered `baseAnalysis.failures` to the wrapper failure list and retain `BASE_ANALYSIS` only as a summary after the specific codes. All serialization, policy, observation and runtime boundaries remain unchanged.
