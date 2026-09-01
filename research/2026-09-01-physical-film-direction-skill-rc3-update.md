# Physical film direction skill update after RC3

Date: 2026-09-01

The reusable skill at
`/Users/mengyingli/.codex/skills/physical-film-direction` now carries the RC3
lessons without embedding the D1 or H1 project identity into future execution.
It adds restricted declarative graph transfer, measured relation-event beats,
full bounded-clip inspection, asymmetric solver outcomes, and separate handling
for render-byte and physical-motion reproducibility.

Updated hashes:

- `SKILL.md`: `93e8ad93724c6e9316a67385b3e5428caefc551273bb1d85553e0e654f1ed4d3`
- `references/validated-patterns.md`: `95c235d69f9e03401539bfe530d587e419ca105003e90301c27886ea64edb8b3`

The skill-creator quick validator passes using `/usr/bin/python3`. The default
Homebrew Python lacked the validator's YAML dependency; no package was
installed and the skill content did not need correction.
