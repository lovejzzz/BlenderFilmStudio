# B59-G0-R3-D2-C1 · Docker inspect capture correction

Date: 2026-08-29  
Status: PREREGISTERED BEFORE ANY COLIMA MUTATION

## Observation

The first D2 launch exited at `INITIAL_MANIFEST_MATCH` before creating the formal root and before executing `colima stop`. Independent read-only comparison confirmed that the running profile, four full container IDs and metadata, configuration hashes, and sparse-disk identities all still matched the frozen restore manifest.

## Cause and correction

`docker inspect` returned valid JSON larger than the runner's 32 KiB diagnostic string slice. The process buffer allowed 1 MiB, but the string was truncated before JSON parsing, so the runner safely treated it as a manifest mismatch.

C1 raises only the internal capture limit for the read-only four-container inspect call to 1 MiB. Persisted samples still contain only extracted, bounded fields and retain the original 16 KiB sample ceiling. No action, timing, causal threshold, interpretation, restoration rule, or evidence root changes. The failed attempt produced no formal evidence and caused no interruption.
