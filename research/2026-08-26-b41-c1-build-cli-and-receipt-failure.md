# B41-C1 · Build CLI and receipt-tool failure

Verdict: `LINUX_AMD64_BLENDER_5_2_CANARY_FAILED`  
Docker build exit: `125`  
Container/Blender runs: `0`

## What passed

- Disk admission passed with `134687367168` bytes available and `113212530688` bytes after the 20 GiB projection.
- The official archive downloaded as exactly `384441228` bytes.
- Its SHA-256 was exactly `96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48`.
- Docker raw architecture `arm64` normalized to canonical `aarch64` through the preregistered B41-C1 rule.
- The temporary build root was removed and no B41 container remained running.

## Why the run failed

The local Docker CLI selected the legacy builder because buildx is not installed. That builder rejected the frozen BuildKit-only argument `--progress plain` with `unknown flag: --progress`, returning exit 125 before reading the Dockerfile.

The failed receipt also exposed three independent tooling defects:

1. `hashB41Evidence` did not remove the existing `evidenceHash` field before recomputation, so both parent and correction self-hash gates failed.
2. The OCIO manifest used locale collation; it ordered uppercase `README.md` after lowercase ICC filenames rather than the preregistered bytewise `LC_ALL=C` order, yielding `27b5...` instead of `57f5...`.
3. Correction-mode tool hashes were calculated from the correction library/audit but stored under the parent library/audit URIs, so independent tool verification failed.

B41-C2 must remove only the unsupported progress flag, exclude `evidenceHash` from its self-hash projection, use bytewise relative-path ordering for the OCIO tree, and record the actual correction tool URIs. All scientific, runtime and containment conditions remain frozen.

Artifacts: `experiments/linux-amd64-blender-runtime-canary-v0-2/results.json`, `audit.json`, `build.stdout.log` and `build.stderr.log`.
