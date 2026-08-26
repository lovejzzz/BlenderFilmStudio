# B37 · macOS worker containment canary

日期：2026-08-26（America/New_York）

状态：**`PREREGISTERED_BEFORE_TOOLING_OR_OUTPUT`**

## 平台盘点，不是结果

本机是 macOS 26.5.1 build `25F80`。`/usr/bin/sandbox-exec` 存在，SHA-256 为 `8857d087219f0f39d3e3c163e5d0a0aed690cc22f34b50c7eee3d74f93e69688`，但系统 man page 明确写为 **DEPRECATED**，并建议开发者采用 App Sandbox。Blender 5.2 的现有 Developer ID 签名没有 `com.apple.security.app-sandbox` entitlement；本实验不修改、不重签 Blender.app。

Apple 将 App Sandbox 描述为 entitlement 驱动的 kernel access control，并要求 macOS app/embedded helper 通过签名与 capabilities 配置：

- <https://developer.apple.com/documentation/security/app-sandbox>
- <https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox>
- <https://developer.apple.com/documentation/xcode/embedding-a-helper-tool-in-a-sandboxed-app>

因此 B37 只问：当前机器上的 deprecated SBPL prototype 能否阻断一组安全、受控、可复现的 Blender worker capabilities；它不能晋级为受支持的生产 sandbox。

## 可证伪问题

同一 trusted Blender Python canary 在以下三种 launch cells 中，文件、loopback、child exec 与 inherited environment 的结果是否按冻结矩阵变化：

1. `UNSANDBOXED`：无 sandbox，继承固定假 secret；
2. `SBPL_INHERITED`：deprecated `sandbox-exec` profile，仍继承固定假 secret；
3. `SBPL_SANITIZED`：相同 profile，但 launcher 删除固定假 secret。

每种 cell 两个新 Blender 进程，共六个 PID。Blender 固定使用 `--background --factory-startup --disable-autoexec --python trusted_canary.py`。autoexec 已由 B36 单独验证；B37 的因变量是 OS capability，不是 blend-file script execution。

## 安全 canary

没有外网、真实 secret 或真实工作区外破坏：

- 所有文件都位于 ignored `experiments/worker-containment-v0-1/work/<run>`；
- “outside” 只是 run 内与 worker root 并列的 control directory；
- network 只连接 runner 在 `127.0.0.1` 随机端口上的一次性 TCP server，并发送 cell nonce；
- child 只尝试 `/usr/bin/touch`，目标在 worker root；
- fake secret 固定为 `BFS_B37_NONSECRET_ENV_CANARY_V1`。

runner 在每个 cell 前确认所有 marker/receipt 不存在，逐个运行避免 nonce 竞争。loopback server 不接受非本机地址。

## 冻结 profile

SBPL prototype 以 `allow default` 为基线，只显式：

- deny `network*`；
- deny sibling control directory 的 `file-read*` 与 `file-write*`；
- deny `process-exec`，仅允许初始 exact Blender binary。

这是 capability canary profile，不是最小权限生产 profile。即使所有 deny 生效，其他未测 capability 仍保持允许。

## 冻结期望矩阵

| Capability | UNSANDBOXED | SBPL_INHERITED | SBPL_SANITIZED |
|---|---:|---:|---:|
| worker 内写入 | allow | allow | allow |
| sibling control read | allow | block | block |
| sibling control write | allow | block | block |
| loopback connect | allow | block | block |
| `/usr/bin/touch` child | allow | block | block |
| fake secret visible | yes | **yes：预期反例** | no |

UNSANDBOXED 的两次重复必须 12/12 capability success，证明 canary 本身可达；否则 `BASELINE_INVALID`。四个 sandbox cell 的 outside read/write、loopback 和 child 共 16/16 必须 block。六个 cell 的 worker 内 report write 都必须成功。

environment counterexample 不是失败噪声：kernel sandbox 不能撤回 launcher 已继承的字符串。SBPL_INHERITED 必须 2/2 看见固定假 secret，SBPL_SANITIZED 必须 0/2；如果观察不同，按冻结 gate 判废或不支持，不能事后改故事。

## 九个 analyzer attacks

正式判决前必须分别注入并被拒绝：sandboxed outside-read success、outside-write success、loopback success、child success、worker write 缺失、inherited-env 反例缺失、sanitized 后 secret 可见、duplicate PID、sandboxed nonce 出现在 loopback receipt。

## 判决

- `DEPRECATED_SBPL_CANARY_SUPPORT_WITH_ENV_COUNTEREXAMPLE`：全部 gates 与九个 attacks 通过；只支持当前主机上的窄 prototype；
- `SBPL_BOUNDARY_NOT_USABLE`：Blender 不能在 profile 下完成 trusted probe，或任一 capability deny 失败；
- `BASELINE_INVALID`：UNSANDBOXED 不能证明 canary 原本可达；
- `RUN_INVALID`：runtime identity、PID、process、report、nonce 或 preflight 失败。

## 明确非结论

不声称生产级、受支持或未来稳定；不声称 parser memory safety、GPU、DoS、全部文件/网络/syscall 隔离；不访问外网或真实 secrets；不重签 Blender；不声称环境清理本身能 contain compromised process。

若 prototype 通过，下一工程选择仍应是 disposable VM/container 或拥有正式 App Sandbox entitlement 的独立 worker host。若不能通过，则直接记录 macOS native path 不可用，不继续扩大 SBPL profile 直到“看起来能跑”。

冻结合同：`specs/worker-containment-spec.v0.1.json`
