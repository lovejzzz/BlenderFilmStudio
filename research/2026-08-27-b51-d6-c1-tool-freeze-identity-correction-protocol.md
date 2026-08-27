# B51-D6-C1 · tool-freeze identity correction protocol

Status: preregistered after the D6 tool-identity failure and before the corrected analyzer run.

## Failure

The first analyzer invocation received `bd82b15a62e12afddf0d0ac218bef84d661b40cb` as its full tool-freeze commit. The actual commit created by the tool-freeze step is `bd82b15840115655fb4f508177b6024c722ccbd6`. The provided object does not resolve in Git.

The analyzer completed and wrote one JSON file, but that file cannot pass the frozen-tool audit and is rejected regardless of its reported result. The attempt launched zero Blender processes, performed zero renders and did not modify any input EXR.

Compact failure evidence is frozen at `experiments/native-cpu-data-pass-semantic-equivalence-tool-identity-failure-v0-1/failure.json`. The invalid generated result has SHA-256 `8916a0072effaae03ae210104e8275dfb965efce8414daa0458ab99e330f197f`, is not retained, and cannot be promoted.

## Single correction

The corrected formal run must:

1. keep the D6 spec, thresholds, analyzer and audit byte-identical;
2. use preregistration commit `b17e2a3fdd11605f13b912bab256befa6579510a`;
3. use the exact resolvable tool-freeze commit `bd82b15840115655fb4f508177b6024c722ccbd6`;
4. begin with an empty formal output root;
5. run the analyzer once and the independent audit once;
6. accept only a valid verdict with 16/16 attacks, byte-exact replay, 2/2 frozen tools and 32/32 retained artifacts.

No metric, threshold, input, code path or interpretation boundary may change in C1.
