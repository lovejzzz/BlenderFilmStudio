# B42 · Nested writable mountpoint rejected before Blender launch

B42 rejected its target verdict before Blender started. The independently regenerated B01 and B02 plans did match their frozen serialized SHA-256 and internal `planHash`, but all five Docker launches exited 125.

The outer repository bind was read-only at `/repo`. The runner then asked Docker to place the writable output bind at `/repo/worker-output`, a path absent from the image and from the mounted repository. OCI attempted to create that destination after applying the read-only mount and failed with `read-only file system`. This is a mount topology defect, not a Blender compiler result.

The failure also exposed a second defect: the analyzer assumed every launch had produced an observation and dereferenced `run.observed.manifest` after the launch failures. The raw generated plans and per-attempt stdout/stderr logs are preserved with `failure.json`; no B42 acceptance result exists.

A correction must be separately preregistered. It may only add a pre-existing `/repo/worker-output` mountpoint and make analysis total over null observations. All identities, benchmarks, resource limits, acceptance rules, and the five-container design remain frozen.
