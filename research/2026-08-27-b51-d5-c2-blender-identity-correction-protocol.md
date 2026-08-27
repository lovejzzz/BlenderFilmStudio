# B51-D5-C2 · Blender executable identity correction

Status: preregistered after the retained C1 retry failure and before correction tooling or render output.

## Retained failure

After C1 repaired OCIO identity, D5 passed all parent/source/OCIO checks and stopped at the Blender executable gate. The spec declared an unrelated `249616`-byte identity; the installed binary and the exact H1 parent both bind the same `183237520`-byte Blender 5.2.0 LTS executable.

The immutable failure is `experiments/native-cpu-data-pass-sample-cost-blender-identity-failure-v0-1/failure.json`, SHA-256 `607e2c9b4841018b5fff2e94df4f146ee64936c5d63b84a650c13776065cedb5`. It records zero Blender child processes, zero renders, zero EXRs and no scientific observation.

## Only allowed correction

C2 may replace the D5 spec's Blender identity with the already-bound H1 values:

- executable: `/Applications/Blender.app/Contents/MacOS/Blender` (unchanged);
- version label: `5.2.0 LTS`;
- SHA-256: `60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`;
- bytes: `183237520`.

The runner's D5 spec SHA constant must bind the resulting corrected spec. No other spec or tool behavior may change. Corrected source must be committed and pushed before retry; any new failure is retained separately.

C2 repairs admission provenance only. It cannot support data-pass exactness, timing or cost claims.
