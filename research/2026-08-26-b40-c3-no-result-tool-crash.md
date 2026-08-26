# B40-C3 · No-result tool crash

Status: `NO_RESULT_TOOL_CRASH`  
Tool freeze commit: `2126b6ff726979e76afa3dac52108744a18c1de7`  
Protocol commit: `0e86ae3eea349bf8666cf0f233a566c3da78d9fe`

B40-C3 crashed before creating an experiment directory, result JSON, attack vector or audit input. The frozen projection helper attempted to read:

```text
c2Spec.serializationCorrection.preregistrationCommit
```

The B40-C2 spec describes its parent corrections but does not contain its own preregistration identity under that path. The identity is frozen by the B40-C2 library constants. Node raised:

```text
TypeError: Cannot read properties of undefined (reading 'preregistrationCommit')
```

No formal B40-C3 decision exists. No raw capacity observation from this invocation is promoted because the runner stopped before evidence hashing and writing. No container, Blender, Colima mutation or other runtime operation occurred.

B40-C4 may change only the C2 projection identity source: import and use `B40_C2_PREREG_COMMIT` and `B40_C2_SPEC_SHA256`. Failure-code projection, serialization-stability logic, capacity policy, probes and attacks remain unchanged.
