# PB.3 C4-C1 inert tool freeze v1.3

Date: 2026-08-31

Verdict: `PASS_STATIC_32_OF_32_INERT`

## Frozen implementation

C4 preserves the complete corrected C3 semantic and resource contract while
implementing the two preregistered harness changes:

- `blender/run_ai_native_studio_pb3_combined_c4.py`, SHA-256
  `a516dbe7c06c477fbc1b36e8dcbad7cef0f3992af4e30bf8418c3efa59f91114`,
  differs from the C3 helper by exactly two adjacent lines immediately before
  `save_as_mainfile`: set file preview type to `NONE`, then assert it;
- `specs/ai-native-studio-pb3-validation-tool-freeze-c4-corrected.v1.2.json`,
  SHA-256 `24baa8e6a03d62fa2559c939209cfe05fb7a9cdbdbe82ec08267aa1bc9ad827d`,
  differs from the C3 corrected tool at exactly `tools.blenderProbe` and
  `tools.blenderProbeSha256`;
- `scripts/run-ai-native-studio-pb3-validation-c4.py`, SHA-256
  `eb670c264cc240b792a55cd9fd3e6a517fcf58a451a4499168a6bd85f7fb929b`,
  resolves the single tool-contract option before delegated authority checks
  and process creation, then preserves C3 process/resource verification;
- `scripts/audit-ai-native-studio-pb3-validation-c4.py`, SHA-256
  `a212b64b3b74b8056478ce70f5f981c51f23d8ea849650720235f34651b22d4e`,
  independently reconstructs the four absolute argv arrays and eight logs,
  runs the frozen base semantic audit, binds both retained attempts and rejects
  every EXR/PNG/JPG/JPEG/MOV/MP4 anywhere in the future work root.

The active execution-tool contract is
`specs/ai-native-studio-pb3-validation-c4-c1-execution-tool-freeze.v1.3.json`,
SHA-256 `cd02bb9264b951c52217d2cdbdd4f5e237a95c071e7533c75eeabdd5f00792c2`.
Its only difference from the failed static-tool contract is the versioned C1
correction binding, new static-auditor path/hash, parent binding, template path
and claim text. The runner, formal independent auditor, helper, corrected tool,
authorization request and thresholds are unchanged.

## Static and negative evidence

The versioned static auditor
`scripts/audit-ai-native-studio-pb3-tool-freeze-c4-c1.py`, SHA-256
`1e402b6c8fa8748b24001fa9d4d3615dc7a5a538030db7442a1f3f6a46015f7b`,
differs from the retained failed static auditor at exactly one message
substring. It continues to require a nonzero inert exit.

The audit at
`experiments/ai-native-studio-phase-b/PB.3-c4-c1-tool-freeze-2026-08-31-mac-m2max-attempt-02/audit.json`
passes 32/32. File SHA-256 is
`d9df9f62d0b3f8bfa18b7cb7b6b00146708f759acae7ed41afec95a89aefca7d`;
self hash is
`c323b9ce28ebbb4b709d46fe22dfa6041f2389a401606cd0420009ca06634cc5`.
The evidence root contains one 3,095-byte file with manifest SHA-256
`b6eea16aeb639ed733ecfb1230ab28e92ad07c108bb9d184b11c33f670f4d6ce`.

The checks cover exact tool/helper diffs, every tool hash, AST power imports,
absolute normalization order, the unchanged six forbidden artifact extensions,
13/13 inputs, both retained attempt manifests, source/binary identity, resource
ceilings, runner self-test and the inert draft rejection. Attempt-03 work and
evidence roots were absent before and after. Blender, proposal, BuildPlan,
scene/save/reopen, render, network and engine-write counts were all zero.

## Authorization boundary

The inert template is
`specs/ai-native-studio-pb3-validation-execution-c4-c1-template.v1.4.json`,
SHA-256 `a7ce9b8c09a5b7e688da52347f9e9584349c750e1119294668fbd6967582e1a0`.
The exact request remains
`specs/ai-native-studio-pb3-validation-only-authorization-request-c4.v1.2.json`,
SHA-256 `865ed150d7d0dfc7b26a32111b6e11b53eccc7a6da288f69d0bdd97703e44871`.

No attempt-03 authority exists. General continuation or earlier PB.3
authorization is insufficient. A future run requires the request's exact text,
then a separately committed single-path execution contract. This tool freeze
does not authorize rendering, `film-engine` mutation or PB.4–PB.7.
