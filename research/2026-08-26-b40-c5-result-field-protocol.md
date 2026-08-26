# B40-C5 · Replay-result field lifecycle correction

Status: `PREREGISTERED_RESULT_FIELD_CORRECTION_BEFORE_TOOLING_OR_OUTPUT`  
Date: 2026-08-26

B40-C4 passed base analysis, 14/14 attacks and replay equality, but added `replayPassed` after evidence hashing. B40-C5 moves that field into evidence before hash and attack generation. A failed replay must flip the field and recompute the hash before persistence; final result assembly may not add it again.

All projection, failure-code, serialization, parser, capacity and zero-runtime behavior remains unchanged. The strongest accepted verdict remains `WORKER_HOST_CAPACITY_BLOCKED_REPLAY_STABLE`.
