# B42-C1 · SceneSpec compiler reproducibility passes on the Linux/amd64 worker

## Result

`LINUX_AMD64_COMPILER_REPRODUCIBLE_AFTER_MOUNT_CORRECTION`

The exact retained Blender 5.2 Linux/amd64 image compiled B01 and B02 twice in four independent, constrained containers. A fifth container rejected the deliberately falsified B01 `planHash`. The independent audit passed with tool, plan and output observations all matching.

## Observed evidence

| Benchmark | Run A | Run B | Plan bytes equal | Canonical structure equal | Frozen structure hash |
| --- | ---: | ---: | --- | --- | --- |
| B01 | 9,685 ms | 9,678 ms | yes | yes | `c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b` |
| B02 | 9,776 ms | 9,361 ms | yes | yes | `025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856` |

For both benchmarks, each regenerated BuildPlan also matched the previously frozen serialized file SHA-256 and internal `planHash`. Every successful scene manifest bound the expected plan hash, OCIO identity and expected structure hash. The tampered plan exited 1, emitted `BuildPlan hash mismatch`, and wrote no scene outputs. No experiment container remained running.

The two `.blend` files for each benchmark were not byte-identical. This repeats the earlier Darwin observation and confirms why BFS uses canonical semantic scene structure—not `.blend` bytes—as the reproducibility criterion.

## What this establishes

The third workflow gate is now experimentally closed for the two benchmark scenes:

`SceneSpec → immutable BuildPlan → contained Blender 5.2 Linux/amd64 compiler → scene.blend + manifest + canonical structure`

This is stronger than proving Blender can launch. It demonstrates that the agent-facing structured contract can produce repeatable Blender scene semantics across clean worker invocations, with exact input identity and a negative integrity control.

## Remaining limits

This does not establish final pixel quality, Eevee/GPU availability, arbitrary-scene coverage, `.blend` byte identity, production throughput, or remote attestation. B41-D3 still constrains the current image to a confirmed compile/Cycles-CPU worker on this host; Eevee needs a GPU-capable or deliberately rebuilt software-render worker.

Machine-readable evidence:

- result SHA-256: `c9a55fb87bf1115960c3c82bfe5eb71b14f4f0ec0df7059e57b842b52160a1a4`
- independent audit SHA-256: `46579e29a27a3ab9937b88e290a83fe2143600772982274be1e94f9239b85834`
