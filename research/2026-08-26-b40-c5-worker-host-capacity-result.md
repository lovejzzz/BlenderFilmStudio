# B40-C5 · Worker host capacity admission result

Verdict: `WORKER_HOST_CAPACITY_BLOCKED_REPLAY_STABLE`  
Attacks: `14/14`  
Independent audit: `PASS`  
Runtime operations: `0`

## Accepted evidence chain

B40-C5 is the first accepted result in the B40 chain. It does not erase:

- B40 attempt 1: invalid `flags:` parser;
- B40-C1: in-memory alias broke persisted replay;
- B40-C2: specific base failure codes were not projected;
- B40-C3: no-result projection-identity crash;
- B40-C4: `replayPassed` was added after evidence hashing.

Each failure has its own immutable protocol/tool/evidence or crash note. C5 changes only the final result-field lifecycle.

Tool freeze commit: `e44f6f237cf67cb95bcb547ce13ef0c03e5f997c`  
Evidence self-hash: `80ac1667677f591d3c8bae9edd3180a5ca410d2c7ccc30d1e128dc2df1a243f4`

## Measured capacity

### Host disk · blocked

- available: `19670355968 B`;
- projected write: `21474836480 B`;
- free after projection: `-1804480512 B`;
- required reserve: `107374182400 B`.

Decision: `HOST_DISK_RESERVE`.

### VM memory · blocked

- Colima configured memory: `6 GiB`;
- Linux `MemTotal`: `6197444608 B`;
- frozen worker ceiling: `8 GiB`;
- BFS infrastructure reserve: `2 GiB`;
- required VM total: `10 GiB`.

Decision: `VM_MEMORY_CAPACITY`.

### VM CPU · blocked

- online CPUs: `4`;
- frozen worker ceiling: `4`;
- infrastructure reserve: `1`;
- required total: `5`.

Decision: `VM_CPU_CAPACITY`.

### Docker storage · blocked

- total: `10461925376 B`;
- used: `5272678400 B`;
- available: `4635705344 B`;
- pre-build safety floor: `8589934592 B`.

Decision: `DOCKER_STORAGE_CAPACITY`.

## Passing gates

- VM swap: `0 B`;
- running containers: `0`;
- x64 emulator: enabled `qemu-x86_64`;
- interpreter: `/usr/bin/qemu-x86_64`;
- flags: `POCF`.

The emulator gate proves registration only. It does not prove Blender can execute correctly under QEMU.

## Replay and attacks

All decision records use value copies. Base analysis, decision, evidence hash and the ordered 14-attack vector were identical before and after JSON round-trip. The independent audit reloaded the persisted result and reproduced all 14 primary failure codes and the same round-trip vector.

Result file SHA-256: `8b3ac036deeb3fd283cb77e1d9c9a05deb22957449ef7905a4e219c9fca85100`  
Audit file SHA-256: `e62019953c59c639fdf119a7f0e4962a1d3cfb70243a3fad04ecf12f84fbb868`

## Strongest supported claim

The current Colima/Docker host is not eligible to start the B41 Blender x64-emulation worker experiment under the frozen BFS operational policy. Four independently replayable capacity gates block it; swap, emulator registration and competing-container gates pass.

## External changes required before B41

At minimum:

1. restore host disk so 20 GiB projected write still leaves 100 GiB free;
2. reconfigure Colima to at least 10 GiB memory;
3. reconfigure Colima to at least five CPUs;
4. provide at least 8 GiB free Docker storage before the trusted image build;
5. rerun a clean admission attempt and preregister B41 separately.

Changing Colima requires a restart and may affect other workloads. B40-C5 does not authorize it. No cleanup, reconfiguration, container or Blender runtime occurred.
