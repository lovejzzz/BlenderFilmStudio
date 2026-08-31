# PB.3 C5 tool-freeze attempt-01 retained failure

Date: 2026-08-31  
Verdict: `FAIL 29/30`  
Formal counts: all zero

The C5 runner, independent auditor, inert execution template, exact request,
and tool-freeze contract were exercised only through static/self-test and an
inert-template negative control. No Blender process or attempt-04 root was
created.

The sole failed check was `inertTemplateRejected`. The runner exited nonzero,
but the observed safe error was a Python callback-arity defect rather than the
expected authorization-status rejection:

`TypeError: main.<locals>.c5_authority() takes 2 positional arguments but 3 were given`

The unchanged C4 runner invokes its replaceable authority hook with three
arguments: the C3 module, C4 contract path, and C4 contract. C5 attempt-01's
local hook accepted only the latter two. A future C2 correction may change only
that callback signature by adding the unused first parameter; all other runner
bytes, semantic tools, auditor logic, thresholds, roots, and permissions remain
frozen.

Evidence:

- audit: `experiments/ai-native-studio-phase-b/PB.3-c5-tool-freeze-2026-08-31-mac-m2max-attempt-01/audit.json`
- file SHA-256: `26216389760bf6e5499cadb1f9697265ae590d1cd193c2849d72abf3b320a7cb`
- self hash: `0d8cdbccf81c4d55b1fc6211454905ac5b011218773a34888b9f1e4b152c3ce6`
- attempt-04 roots before/after: absent
- Blender/proposal/BuildPlan/render/network/engine-write counts: all zero

This failure grants no attempt-04 execution authority.
