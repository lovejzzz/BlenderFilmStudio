# B38 · Worker launch contract result

日期：2026-08-26（America/New_York）

正式判决：**`WORKER_LAUNCH_CONTRACT_LOGIC_SUPPORT_ONLY`**

runtime 判决：**`NO CHILD PROCESS · NO BACKEND CONTAINMENT CLAIM`**

## 冻结身份

- preregistration commit：`a7d8311e0af46824aafafaa25d0c17be8a86cc44`
- spec SHA-256：`c96a6c7d9bf91c0b0f72fa2094ef6b6c0bb778d7443533f661859427715f9514`
- tool-freeze commit：`41798b328b324ba4abf1786b4a853060ccb5154a`
- Node：`v26.5.0`
- Node binary SHA-256：`70851490e028b3d699a8d6d4e1de909af2a989359ae807974c92af9c6580a8e8`
- macOS：26.5.1 build `25F80`，arm64

B38 只编译、canonicalize 与审计 JSON。没有调用 Blender、Docker 或 shell，没有创建 container，也没有读取真实 secret。

## 三个 canonical request → plan 对

COMPILE、RENDER、AUDIT 三个冻结 request 都创建了 deep-reordered JSON clone。对象 key 顺序改变，array 语义不变。

| Fixture | Request SHA-256 | LaunchPlan SHA-256 | Reordered equal |
|---|---|---|---:|
| P1 / COMPILE | `1d699d6a…954fe` | `acc590e1…ab818` | yes |
| P2 / RENDER | `fcda5978…f1234` | `e2ca20ce…1885d` | yes |
| P3 / AUDIT | `cc4dd05c…4a8d2` | `31d488b1…e1941` | yes |

3/3 request hashes 与 3/3 self-hashed plan hashes 都跨 reorder 相同。每个 plan 的 environment exact 11 keys；parent 中刻意加入的固定非秘密 canary 没有进入任何 plan。

每个 plan 固定：

- `shell:false`；
- byte-pinned Blender executable identity；
- `--background --factory-startup --disable-autoexec --offline-mode` prefix；
- `--python-exit-code 1`；
- `/inputs` 唯一 read-only host mount，`/outputs` 唯一 writable host mount；
- digest-only image reference、`pull=never`、read-only rootfs、network none、non-root、drop-all caps、no-new-privileges，以及 PID/memory/CPU limits。

最后一组是 future container candidate policy 的数据合同，不是已经生效的 Docker 观察。

## admission 与磁盘反例

synthetic admission 正例在 140 GiB available、20 GiB projected 时留下 120 GiB，得到 `ACCEPTED`。dirty output root 即使空间充足仍 `BLOCKED`。119 GiB available 减 20 GiB 后只有 99 GiB，也按冻结规则 `BLOCKED`。

正式运行同时读取了真实 host：available `24,230,027,264 B`，减默认 projected `21,474,836,480 B` 后只剩 `2,755,190,784 B`，远低于 100 GiB reserve，因此 `hostAdmission=BLOCKED`。这个观察没有被 override；它是 B39 不得启动 container/Blender 的直接证据。

## terminal receipt 状态机

四个 synthetic terminal receipts 都通过 self-hash 与 plan binding：

| Status | Exit / state | Promotable |
|---|---|---:|
| `SUCCEEDED` | exit 0，report/output identity complete | yes |
| `FAILED` | exit 7 | no |
| `TIMED_OUT` | SIGTERM → 5 s grace → SIGKILL policy | no |
| `CANCELLED` | cancelled | no |

B38 没有真的发送 signal；它冻结以后 backend runtime 必须留下的状态。automatic retry 仍为 false，retry 必须使用新 attempt id 与新 empty output root。

## 25 个攻击与独立 audit

25/25 frozen attacks 被拒绝，覆盖：environment inheritance/key/path、shell/executable/argv、autoexec/offline/Python failure、image/pull、mount/socket、network/privilege/capability/user/rootfs/resource limits、disk admission、timeout promotion 与 plan self-hash。

独立 audit 重新读取结果，重算三组 plan、admission、receipts 和全部 attacks，并要求重算 attack JSON 与记录值 exact 相同，得到 `PASS`。

artifact SHA-256：

- results：`42fe3ceb1b36ded93c7cc40f1f0651c82f30a5e8878bcba3c2ec2eeb8454bf17`
- audit：`2c48229f0961faf8b030489ce0c69edd3785797ceeb4fc6e0c25ea990b0204f1`

完整 evidence 只有约 48 KiB。

## 可以说 / 不能说

可以说：一个 backend-agnostic pure compiler/analyzer 已能把冻结 request 稳定编译为 self-hashed launch plan，并对 environment、argv、mount、candidate limits、disk admission 与 terminal promotion 做 fail-closed 审计。

不能说：Blender 已在 Linux container 中运行；Docker/Colima/VM 已阻断 filesystem、network、process、GPU 或 kernel exploit；候选 policy 已被 runtime enforce；Linux Blender、GPU passthrough 或 Cycles/Eevee 兼容性成立。

## 下一可证伪边界

B39 才能测试 disposable Linux backend。它必须另行预注册并在 host disk admission 恢复后运行，至少包含：

1. digest-pinned Blender worker image 与 SBOM/provenance；
2. read-only input、single output、read-only rootfs、tmpfs work；
3. no network、non-root、drop-all caps、no-new-privileges；
4. cgroup PID/memory/CPU limits及实际 breach；
5. Blender trusted canary 正例与 sibling read/write、network、child、environment 负例；
6. timeout/kill、dirty-output quarantine、new-attempt recovery；
7. 对 container/VM/daemon trust boundary 的明确非声明。

当前不能因为已有 Alpine image 就把 B39 当作已完成，也不能在 100 GiB reserve 以下启动它。

## 公开 artifacts

- `specs/worker-launch-contract.v0.1.json`
- `experiments/worker-launch-contract-v0-1/results.json`
- `experiments/worker-launch-contract-v0-1/audit.json`
- `scripts/lib/b38-worker-launch-contract.mjs`
- `scripts/run-b38-worker-launch-contract.mjs`
- `scripts/audit-b38-worker-launch-contract.mjs`
