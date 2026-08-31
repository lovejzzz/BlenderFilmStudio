# PB.3 validation-only C3 attempt-02 retained failure

Date: 2026-08-31

Verdict: `FAIL_HARNESS_POST_SEMANTIC_EXECUTION`

Scope: PB.3 validation-only; zero render; no engine mutation or remote write

## Authority and immutable roots

The owner supplied the exact authorization frozen in
`specs/ai-native-studio-pb3-validation-only-authorization-request-c3.v0.8.json`.
The one-path execution contract is
`specs/ai-native-studio-pb3-validation-only-execution-c3.v1.0.json`, file
SHA-256 `2bcc7d75bd678b0f6ca5d992fbad7f78098bb9aabc04ac0eca37b14e31603258`,
committed as `e8d5a62476436f308bc996e4885ac1d906066350` with parent
`8dd8e2128e042b874f21e3eafb577a7f8037e798`.

The retained work root is
`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.3-2026-08-31-mac-m2max-attempt-02`:

- 29 regular files;
- 842,437 bytes;
- manifest SHA-256 `6b12f0b8f2545a3463902638540a87981542a7f202b3cef161ad482458c97ca8`.

The retained evidence root is
`experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-02`:

- 15 regular files;
- 47,794 bytes;
- manifest SHA-256 `4d0930b596128fcaf3019777cc586046f4c5b10fc1a11bf60536a12c9620262e`.

Both roots are immutable. Do not delete the two thumbnail files, rewrite the
receipt/audits, or retry in these roots.

## What passed

The frozen base runner completed all four authorized zero-render Blender
starts. B01 and B02 each completed one exact approved proposal execution and
BuildPlan write, one semantic scene build and workspace save, and one reopen
with Expert-state roundtrip. All four processes exited zero. The eight durable
stdout/stderr logs match the hashes in the receipt. The base semantic checks
for probe roster, probe content, BuildPlans and semantic structures all pass.

The receipt reports the exact authorized counts: 4 Blender starts, 2 proposal
executions, 2 BuildPlan writes, 2 scene builds, 2 workspace saves, 2 reopens,
and zero renders, network calls, engine source edits or engine remote writes.
Its file SHA-256 is
`e5bd63251d51ab31a3f9def21cc296c39ac1c2005600bfaf5d36b058742d4397`
and self hash is
`b8c0616b3c7fb14c2b7b418ce561b1981126dcd4a0535adea5b4b0147277acc0`.

## Why the attempt fails

The C3 runner rejected the completed base receipt at its post-run argv gate.
All four recorded argv arrays contain the relative value
`specs/ai-native-studio-pb3-validation-tool-freeze-c3-corrected.v0.8.json`
after `--tool-contract`; the C3 reconstruction resolves that same argument to
an absolute path. This is a spelling-normalization defect in the C3 wrapper,
not a process or log mismatch.

The frozen base auditor independently returns `FAIL 17/18`. Its sole false
check is `noRenderArtifacts`. Saving each `.blend` caused Blender to write one
2,949-byte OS thumbnail-cache PNG under the isolated HOME at the same second as
the save:

- B01: `isolation/b01/home/.thumbnails/large/86c496608fb0ffec566b5dc171349004.png`,
  SHA-256 `07e14378ed0afeff449debf8a5f060a4882eeb79dab578c2d63f35781f43158b`;
- B02: `isolation/b02/home/.thumbnails/large/d1087370e5b4df6f672b7c4451e76dbc.png`,
  SHA-256 `37f3614ec12487d8cb8d0fc6b4d33d991c47de5e8ccc76728aa01e43a58102b9`.

The audit deliberately treats any PNG anywhere in the work root as a render
artifact, so the observed thumbnail cache fails the frozen gate even though
the process receipts and logs report zero rendering. The threshold is not
relaxed after observation.

The consolidated independent audit returns `FAIL 21/23`; its only false checks
are `baseAuditPass` and `processArgvAndLogsExact`. All eight log records within
the latter composite check are individually exact. Its file SHA-256 is
`b4fde05a2c20ed66a720a087c2cbfd86f5a66e9577c401c056fd68f51272cc84`
and self hash is
`d85dd5896fd7bfa1848b9367b136a0d0844d9ca8aa1dc02dea7982fa5081908b`.
The base audit file/self hashes are
`08d715d5787e273b26e95acef6be597bcab6ef94eae62e12c26b952df2946797` /
`b002779715ce73064bf9436eb6b7e922165290afe6aacafc2af25e2dfac908ef`.

## Bounded next correction

A future versioned correction may preserve every semantic threshold while:

1. normalizing the runner's `--tool-contract` argument to the same absolute
   spelling before process creation and independent reconstruction; and
2. setting Blender's `preferences.filepaths.file_preview_type` to `NONE`
   before workspace save, preventing OS thumbnail-cache PNG creation instead
   of excluding an observed artifact after the fact.

That correction requires a new inert tool freeze, static/negative audit,
fresh-root authorization and a new attempt. This attempt supplies no authority
to rerun, mutate `film-engine`, render, or begin PB.4–PB.7.
