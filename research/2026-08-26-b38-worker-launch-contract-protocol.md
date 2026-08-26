# B38 · Worker launch contract protocol

日期：2026-08-26（America/New_York）

状态：**PRE-REGISTERED BEFORE TOOLING OR OUTPUT**

## 为什么是下一边界

B36 只证明 registered Text 的自动执行必须由显式 `--disable-autoexec` 阻断；它不是 parser sandbox。B37 只证明 deprecated SBPL prototype 在这台机器上阻断了四类受控 capability，同时留下“继承环境仍可见”的反例；它也不是受支持的生产 sandbox。B12 的 watchdog 能分类 wall time、RSS、log 与 output breach，但不是 kernel hard limit。

因此，在选择 disposable Linux VM/container 或签名 macOS worker host 前，必须先冻结一个不依赖 backend 的 launcher contract。否则 backend 实验可以通过改变环境、argv、mount、预算或失败语义来“看起来通过”。

## 可证伪问题

可信 compiler 能否把三个冻结 WorkerRequest 的不同 JSON key order 编译为同一 canonical WorkerLaunchPlan，并同时满足：

1. 不继承 parent environment，只生成 11 个 exact allowlisted keys；
2. `shell:false`，Blender executable 与 SHA 固定；
3. argv 以 `--background --factory-startup --disable-autoexec --offline-mode` 开始，并固定 `--python-exit-code 1`；
4. 只有 `/inputs` read-only 与 `/outputs` writable 两个 host mount；
5. future container candidate 需要 digest-pinned image、`pull=never`、read-only rootfs、no network、non-root、drop all caps、no-new-privileges 与冻结 PID/memory/CPU limits；
6. host disk admission 仍要求 projected write 后至少保留 100 GiB；
7. timeout/nonzero/cancelled receipt 永远不可 promotion，且 retry 不能复用 attempt id 或 dirty output root。

完整机器合同：`specs/worker-launch-contract.v0.1.json`。

## 三个正例

三个 request 只改变 job id、scene URI、trusted script URI、script args、projected output bytes 与 output root identity。每个正例创建一个 reverse/deep-reordered JSON clone。原件与 clone 必须分别得到：

- 相同 canonical request SHA-256；
- 相同 canonical launch-plan SHA-256；
- exact environment、argv、mount 与 candidate-policy gate；
- parent fake secret `BFS_B38_NONSECRET_PARENT_CANARY` 不存在。

正例只编译和审计 JSON，不 spawn child、不调用 Docker、不读取真实 secret。

## receipt 状态机

同一冻结 plan 生成四个 synthetic terminal receipt：

- `SUCCEEDED`：exit 0、未 timeout/cancel、report/output identity 完整，唯一可 promotion；
- `FAILED`：nonzero，不可 promotion；
- `TIMED_OUT`：记录 SIGTERM → 5 s grace → SIGKILL policy，不可 promotion；
- `CANCELLED`：不可 promotion。

dirty output admission 与 below-reserve admission 都必须在 launch 前返回 `BLOCKED`。B38 不声称真的发送 signal；它只冻结以后 runtime 必须产生的可审计状态。

## 25 个冻结攻击

正式 analyzer 必须分别拒绝：继承假 secret、缺 env key、env path escape、shell=true、executable identity 变化、缺 disable-autoexec、注入 enable-autoexec、缺 offline-mode、注入 online-mode、Python exit code=0、image 未 pin digest、pull 非 never、input writable、第二个 writable host mount、Docker socket mount、network 非 none、privileged、cap add、缺 no-new-privileges、root user、rootfs writable、缺 PID/memory/CPU limit、below-reserve 被接受、timeout 可 promotion、plan self-hash变化。

攻击只在 baseline 通过后执行；数量必须 exact 25/25，不允许在看到结果后删改类别。

## 判决

- 全部正例、canonical pairs、receipt/admission gates 与 25/25 attacks 通过：`WORKER_LAUNCH_CONTRACT_LOGIC_SUPPORT_ONLY`。
- 任一 parent-only key 被继承：`ENVIRONMENT_CONTRACT_FAILED`。
- argv、shell、identity、mount、candidate policy、disk admission 或 recovery 不符：`LAUNCH_CONTRACT_FAILED`。
- runtime、prereg ancestry、fixture/attack count 或 hash 自洽失败：`RUN_INVALID`。

即使 support，也只能说 pure contract compiler/analyzer 按冻结规则工作。不能说 Blender 已在 container 中运行，不能说 Linux/Colima/Docker/VM 已形成 production boundary。

## 当前只读 backend 盘点（不属于 B38 判决）

本机 Colima 正在 macOS Virtualization.Framework 上运行，Docker server 为 29.5.2、Linux kernel 6.8.0-117-generic；已有 `alpine:3.20` 与 `debian:bookworm-slim` image。由于 host 只剩约 19 GiB 且 BFS disk guard 已 block，B38 不拉 image、不建 container。该事实只证明未来 B39 有候选 testbed，不证明 backend 合格。

官方接口依据：

- Blender 5.2 CLI：<https://docs.blender.org/manual/en/5.2/advanced/command_line/arguments.html>
- Node `child_process.spawn`：<https://nodejs.org/api/child_process.html>
- Docker `container run`：<https://docs.docker.com/reference/cli/docker/container/run/>
- Docker read-only bind mounts：<https://docs.docker.com/engine/storage/bind-mounts/>

## 冻结顺序

本提交只创建协议与 spec。B38 compiler、analyzer、fixtures、attack runner、results 与 audit 在本提交时都不存在。下一提交才能实现工具；再下一提交才能生成结果。任何 runtime backend 执行必须等待磁盘安全线恢复，并另立 B39 preregistration。
