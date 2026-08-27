# B44 — Codex proposal → Blender worker promotion protocol

Date frozen: 2026-08-26
Status at freeze: `PREREGISTERED_BEFORE_RUNNER_OR_OUTPUT`

## Question

Can the immutable outputs of the already completed B43 Codex subscription holdout cross the deterministic least-authority adapter boundary and enter the already verified Blender 5.2 Linux/amd64 worker without gaining undeclared authority?

## Frozen chain

```text
saved Codex proposal
  → exact file + canonical identity check
  → frozen deterministic adapter decision
  → exact frozen SceneSpec identity
  → exact frozen immutable BuildPlan identity
  → Blender 5.2 Linux/amd64 worker
  → manifest + canonical scene structure + .blend
```

The two accepted proposals are `TABLETOP-A` and `INTERIOR-A`. Each receives two independent empty output directories and two fresh worker containers. `UNAUTHORIZED-A` is the negative case: it must produce zero SceneSpecs, zero BuildPlans and zero Docker launches. The complete experiment therefore has exactly four, not five, worker launches.

## Acceptance boundary

- All three parent evidence pairs and all frozen input hashes must match before execution.
- Each accepted saved proposal must validate and materialize to exactly the frozen SceneSpec; the frozen BuildPlan file and internal `planHash` must match.
- Four real worker processes must exit successfully before the 30-second wall limit under the B42-C1 container contract.
- For each scene, the two canonical structure files must be byte-identical. The resulting structure hash is an observation, not a threshold selected after seeing the run.
- Each compile manifest must bind the expected `planHash` and its own canonical structure hash.
- Docker operations must contain one image inspection, exactly four runs and one final running-container check; build, pull and download are forbidden.
- An independent audit must reconstruct the decision and all 12 adversarial mutations must fail.

## Why structure equality is primary

Blender `.blend` containers may contain volatile serialization details. B42-C1 already showed semantic structure equality while `.blend` bytes differed. B44 therefore records `.blend` byte equality but does not require it. The falsifiable reproducibility claim is the canonical scene structure plus manifest binding from two clean compilations of the same immutable plan.

## Non-claims

B44 is not a live model test, pixel render, visual-quality review, Eevee/GPU test, arbitrary-prompt evaluation, performance benchmark or remote attestation. It does not turn a Codex subscription into a guaranteed unlimited or zero-cost compute service. It tests one narrow promotion boundary using immutable outputs already generated under B43.
