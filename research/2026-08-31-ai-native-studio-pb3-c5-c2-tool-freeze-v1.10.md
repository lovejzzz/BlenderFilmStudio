# PB.3 C5-C2 inert tool freeze PASS

Date: 2026-08-31  
Verdict: `PASS 30/30`  
Formal counts: all zero

## Frozen correction

The versioned C5-C2 runner differs from the retained failed C5 runner by one
line: the local C4 authority callback accepts the unchanged caller's unused
`_c3` argument. No semantic logic changed.

- C2 correction: `specs/ai-native-studio-pb3-validation-c5-c2-runner-callback-arity.v1.10.json`
  - SHA-256: `f225eeb782c5365a349bcd12470f43443eed4fdeafe3ae0b2f942582b04f38bb`
- C5-C2 runner: `scripts/run-ai-native-studio-pb3-validation-c5-c2.py`
  - SHA-256: `9b70c3171ce05d811bda767a11b78b82a17a953ae556b93f3200f7cc968fdf15`
- Independent C5 auditor: `scripts/audit-ai-native-studio-pb3-validation-c5.py`
  - SHA-256: `6b1983efbd14b8560d6d3c5de168a6e6f9adb3a5d2b3b52ba1e2b15241b032f3`
- C5 static auditor: `scripts/audit-ai-native-studio-pb3-tool-freeze-c5.py`
  - SHA-256: `2344da217d451d99968d0207cf09cae741c6ac2a1535f24d1aa5652d5d45c890`
- Execution tool freeze: `specs/ai-native-studio-pb3-validation-c5-c2-execution-tool-freeze.v1.10.json`
  - SHA-256: `0e8c3d339ee4bb2fc82683637ae9458c43b94016becc13faab6106ed38a6a58e`
- Inert template: `specs/ai-native-studio-pb3-validation-execution-c5-c2-template.v1.11.json`
  - SHA-256: `34fa18da24e641d4d63999afed578c869332690e2ac76f1aa81ffb2b18e56bf0`
- Exact authorization request: `specs/ai-native-studio-pb3-validation-only-authorization-request-c5-c2.v1.10.json`
  - SHA-256: `3ef853ff7b8293d0347390f8445b35faba32947451fdf30b91f3061aa11f1d14`

## Static and negative controls

The static auditor passed all 30 checks and a second fresh `/tmp` execution was
byte-identical. It verified:

- exact hashes for all C3/C4/C5 tools and three correction contracts;
- the one-line runner diff and correct inert authorization-status rejection;
- 13/13 frozen inputs;
- unchanged attempt-01/02 manifests and attempt-03 absent-work/evidence manifest;
- fresh attempt-04 work/evidence roots before and after both checks;
- exact source and accepted binary identities;
- four-start/two-operation ceilings, 2 GiB / 64 MiB resource limits, zero
  render/network/engine-write permissions, and all six forbidden artifact
  extensions;
- the independent auditor's real `c3CorrectionSha256` receipt binding without
  inventing an unwritten C4 receipt field.

Evidence:

- `experiments/ai-native-studio-phase-b/PB.3-c5-c2-tool-freeze-2026-08-31-mac-m2max-attempt-02/audit.json`
- file SHA-256: `6567e98fb9c0aa94115226c68a46ef548fe71e8b7a834158cbf43c4daa911660`
- self hash: `e2af854d4ec613a0397520e0ed1d12c4275b667d09817d8a06a13988e365ffa3`
- root: 1 file / 2,080 bytes / manifest `f563fbf05f125ece143d6706d75b51daf829aa371c42b67ecd6dc6efab8d8416`

## Authority boundary

The attempt-04 template remains `DRAFT_AUTHORIZATION_MISSING`; no formal root
or Blender process was created. Only the exact text in the C5-C2 authorization
request can enable one fresh attempt-04. General permission and the consumed
C4 authorization remain insufficient. PB.4-PB.7 stay locked.
