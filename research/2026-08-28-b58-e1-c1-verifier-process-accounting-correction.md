# B58-E1-C1 · Preferred-verifier Blender process accounting correction

Date: 2026-08-28

Status: preregistered before the production orchestrator, official preflight, formal output or any B58 Blender process exists

## The preregistration defect

The frozen B58 parent asks the post-compile recovery to run `verify:production-receipt` while starting “zero additional Blender.” Reading the already frozen verifier bytes shows that these statements cannot both be literal: every successful preferred verifier starts a separate Blender 5.2 process to reopen `scene.blend` with `blender/audit_compiled_artifact.py`. That child is an artifact audit, not a native compile and not a render, but it is still a Blender process.

This was found during implementation review, before the production orchestrator exists and before any official or formal B58 root was created. The parent preregistration remains immutable. C1 corrects only the process taxonomy used to interpret its matrix, one gate and its operation ceiling.

## Frozen correction

The effective no-repeat property is:

> After a valid `PRODUCTION_COMPILE` stage receipt is durable, recovery starts zero additional production compiler wrappers and zero additional native-compile Blender processes. It then starts exactly one preferred verifier, whose fixed implementation starts one Node current-receipt verifier child and one Blender artifact-audit child.

Across the complete formal matrix, the exact process ceiling is therefore:

- 4 production compiler wrappers;
- 4 native-compile Blender starts: 3 successful and 1 deliberately interrupted;
- 3 preferred verifier CLI starts;
- 3 current CompileReceipt Node verifier children;
- 3 Blender artifact-audit starts;
- 7 total Blender starts, partitioned as 4 compile + 3 audit;
- 0 render, model, network and Docker operations.

The parent gate `RECOVERY_STARTS_ZERO_ADDITIONAL_BLENDER_AFTER_COMPILE_CHECKPOINT` is replaced only in the effective mapping by `RECOVERY_STARTS_ZERO_ADDITIONAL_NATIVE_COMPILE_BLENDER_AFTER_COMPILE_CHECKPOINT`. The denominator stays 34. The 72 parent attacks remain, and eight correction attacks cover category substitution, omitted audit children, hidden duplicate compiles and off-by-one totals.

## Matrix interpretation

`BASELINE_B01` has one compile Blender and one audit Blender. `ORCHESTRATOR_EXIT_AFTER_COMPILE_B01` has one compile Blender before exit; recovery has no compile Blender and exactly one audit Blender. `BLENDER_INTERRUPTED_B02` has one interrupted compile Blender, one recovery compile Blender and one audit Blender. `LIVE_PROCESS_REFUSAL` starts neither category.

Any recovery-time native compile after a valid compile-stage receipt remains an immediate rejection, even if a report relabels it as audit work. Conversely, the mandatory artifact-audit child may not be hidden to satisfy the original aggregate wording.

## Unchanged boundary

C1 changes no SceneSpec, BuildPlan, B57 compiler/verifier byte, DAG, manifest, ledger, recovery decision, fault boundary, disk threshold, formal root or film-quality claim. It only makes process accounting compatible with the actual frozen preferred verifier. The next step is to commit and push this correction before implementing the production orchestrator.
