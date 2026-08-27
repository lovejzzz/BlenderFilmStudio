# B52-D12.8-C1 · Typed-envelope parent binding correction

Date: 2026-08-27

Status: `CORRECTED_PREREGISTRATION_BEFORE_FORMAL_OUTPUT`

## Retained defect

The original D12.8 preregistration froze both reused typed-envelope encoder files, but omitted the machine-readable D12.1 spec that both encoders require at runtime. A runner could not execute those tools from the declared parent graph alone.

No D12.8 or D12.8-C1 formal root, render, adapter payload, consumer payload, measurement or verdict exists. The defect was found while implementing the runner, before tool freeze and before formal preflight.

## Sole correction

C1 binds `specs/blender-cross-language-evidence-envelope-development.v0.1.json` at SHA-256 `8bd219570e0c7ec922a671919d680787caf55b2ba7d8a631ed5bc995ab24f116`. It changes the experiment identity to `B52-D12.8-C1`, assigns fresh C1 preflight/formal roots and updates embedded spec hashes after freezing the corrected file.

The scientific question, four fixtures, camera/object transforms, material parameters, structural-validity rule, local-risk formula, threshold, coverage/stress gates, comparator report-only role, process matrix, attacks, runtime and verdict mapping are unchanged.

Original preregistration identity:

- commit: `7f62162`
- spec SHA-256: `67722b1c8fafa0b83518e6e467de1adb9ca88bd32b7145f15be2d5627767b4d4`

Corrected spec SHA-256: `d7e7c0ee0bd7f512766188eabda9fa0dccb098a0729b26487aa38bee97d6aea6`.

Formal evidence remains zero at correction time.
