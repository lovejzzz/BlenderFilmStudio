# B58-E1-C3 · Frozen-package entry correction

Date: 2026-08-29
Status: PREREGISTERED AFTER ZERO-BLENDER REHEARSAL FAILURE, BEFORE OFFICIAL OUTPUT

## Counterexample

The first fresh-clone B58 official-preflight rehearsal reached the preferred B01 production preflight with zero Blender. That child correctly returned `REJECTED / RELEASE_BLOB` with message `Release hash mismatch for package.json`. Its temporary receipt SHA/self-hash were `618aece343a3c01c39e85c2f965201763bb567c5efda26546d72a009f8765aa5` / `ce633332f017f3c51fae469eb90811d7af3d7b2ccf497f69059307021348a8bb`.

B57 freezes `package.json` at SHA-256 `a2235a7558d420c86acb62eafda2c52fbfc1620c1de934fa88e02eea27381520`. Adding B58's requested `job:production` alias changed it to `6d13fa59a730d1b418208bfb7d28bc319b20d120aef98433e60a531fd20960af`. Therefore the literal alias requirement conflicts with the stronger requirement that the already admitted B57 production surface remain byte-exact.

The B58 official roots remain absent. No Blender, render, model, network or Docker process was started by the failed rehearsal.

## Frozen correction

C3 restores `package.json` byte-for-byte to the B57-frozen version. The effective B58 entry is the direct command that the alias would have dispatched:

`node scripts/run-restart-safe-production-job.mjs`

Preflight must prove both the B57 package hash and this exact direct entry. The orchestrator modes, arguments and bytes do not change. Two C3 attacks mutate the frozen package hash and direct command independently; both must be rejected.

C3 changes no DAG, recovery decision, SceneSpec, BuildPlan, process ceiling, disk reserve, formal root or verdict threshold. It preserves the stronger parent production contract instead of weakening B57 to accommodate a convenience alias.
