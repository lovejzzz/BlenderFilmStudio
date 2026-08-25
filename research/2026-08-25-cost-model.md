# Codex CLI + Blender production cost model

Snapshot: 2026-08-25

## Research question

Can a film workflow use Codex CLI for orchestration and Blender for deterministic rendering, avoid generative-video models, and reduce the marginal cash cost to approximately the model subscription?

## Verdict

Directionally yes, under a narrow set of assumptions. If a creator already owns a capable workstation and reusable assets, renders locally, excludes labor from the prototype budget, uses no optional generation APIs, and remains within a ChatGPT plan allowance, the new cash outlay can approach the subscription plus electricity and storage.

That is not the same as zero production cost. A fully loaded model must include:

`TCO = AI orchestration + render compute + hardware amortization + electricity + storage/egress + assets/licenses + human labor + failure/rework`

The recommended unit is:

`cost per accepted second = total production cost / final accepted seconds`

## What removing video models changes

- Removes a per-generated-second model charge from the final-pixel stage.
- Moves pixel synthesis to deterministic Blender rendering.
- Enables character, set, material, camera, and lighting assets to be amortized across shots.
- Allows dependency-aware partial rebuilds instead of regenerating entire clips.
- Does not remove the cost of render hours, assets, animation, lighting, QA, or human review.

## Codex operating modes

1. **Subscription-first, local, supervised.** Sign in to Codex CLI with ChatGPT and use included plan capacity for local interactive work and `codex exec`. This is the lowest-cash prototype path, but allowances are finite and task-dependent.
2. **Metered API automation.** Use an API key for unattended scripts, shared automation, CI/CD, and auditable scaling. Route routine work to a lower-cost model and escalate difficult tasks.
3. **Studio scale.** AI orchestration remains metered, while asset labor, render nodes, storage, animation cleanup, and QA increasingly dominate total cost.

## API price snapshot

Published standard short-context prices per 1M tokens at the snapshot date:

| Model | Input | Cached input | Output | Illustrative 10M input + 1M output |
|---|---:|---:|---:|---:|
| GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | $3.20 |
| GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | $32.00 |
| GPT-5.6 Sol | $4.00 | $0.40 | $20.00 | $60.00 |

The illustrative workload assumes no cached tokens. It is not a per-film estimate.

## Conditions for “almost subscription only”

All must hold:

1. Existing capable workstation.
2. Local rendering only.
3. Existing or free assets.
4. Human time treated as R&D rather than production cost.
5. Codex usage remains within the plan allowance.
6. No optional image, 3D, motion, audio, or video generation APIs.

## Measurement schema for the first experiment

For every shot, record:

- Codex authentication mode and model.
- Input, cached-input, and output tokens.
- Scene build and render hours.
- Measured power and device identity.
- Hardware utilization and amortization policy.
- Asset IDs and reuse counts.
- Storage generated and retained.
- Human minutes by task category.
- Failure reason, retry count, and first-pass acceptance.
- Final accepted duration.

## Sources

- [OpenAI — Codex plans, limits, and pricing](https://learn.chatgpt.com/docs/pricing)
- [OpenAI — Codex CLI](https://learn.chatgpt.com/docs/codex/cli)
- [OpenAI — Codex authentication](https://learn.chatgpt.com/docs/auth)
- [OpenAI — API pricing](https://developers.openai.com/api/docs/pricing)
- [Blender Foundation — License](https://www.blender.org/about/license/)
- [Blender 5.2 Manual — Cycles render settings](https://docs.blender.org/manual/en/5.2/render/cycles/render_settings/index.html)

Prices and plan limits are time-sensitive. Blender licensing is zero-cost for use, but distributed Blender add-ons that depend on `bpy` require separate GPL compliance review.
