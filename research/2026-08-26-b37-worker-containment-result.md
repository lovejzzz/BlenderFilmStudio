# B37 · macOS worker containment canary result

日期：2026-08-26（America/New_York）

正式判决：**`DEPRECATED_SBPL_CANARY_SUPPORT_WITH_ENV_COUNTEREXAMPLE`**

生产判决：**`NOT A SUPPORTED PRODUCTION SANDBOX`**

## 冻结身份

- preregistration commit：`5b9a85c`
- spec SHA-256：`f1069f81a40abf407323f0df3be8b343d6123330201330f1cc12f049fccc7005`
- tool-freeze commit：`210418a`
- macOS：26.5.1 build `25F80`
- `/usr/bin/sandbox-exec` SHA-256：`8857d087219f0f39d3e3c163e5d0a0aed690cc22f34b50c7eee3d74f93e69688`
- Blender：5.2.0 LTS build `fbe6228777e7`

系统 man page 明确把 `sandbox-exec` 标为 deprecated；Blender 当前签名没有 `com.apple.security.app-sandbox` entitlement。本实验不修改或重签 Blender。

## 真实 Blender 六进程结果

所有 canary 都留在 ignored run root。network 只连接一次性 `127.0.0.1` server；“outside” 只是 worker root 的 sibling control directory；secret 是固定非秘密字符串；child 只尝试 `/usr/bin/touch`。

| Cell class | PID | Worker write | Outside R/W | Loopback | Child exec | Fake secret |
|---|---|---:|---:|---:|---:|---:|
| UNSANDBOXED_A | 93378 | allow | allow / allow | allow | allow | visible |
| UNSANDBOXED_B | 93380 | allow | allow / allow | allow | allow | visible |
| SBPL_INHERITED_A | 93382 | allow | block / block | block | block | **visible** |
| SBPL_INHERITED_B | 93385 | allow | block / block | block | block | **visible** |
| SBPL_SANITIZED_A | 93388 | allow | block / block | block | block | absent |
| SBPL_SANITIZED_B | 93391 | allow | block / block | block | block | absent |

六个 PID 全部唯一，6/6 exit 0、无 timeout、runtime identity 与 report 通过。UNSANDBOXED 12/12 capability success，证明 canary 原本可达。四个 sandboxed cell 对 sibling read/write、loopback 与 child exec 共 16/16 返回 `PermissionError`；6/6 worker 内写入仍成功。

loopback server 只收到两条 UNSANDBOXED nonce，且都与 cell 精确绑定；四个 sandbox cell 没有 receipt。

## 环境继承反例

SBPL_INHERITED 2/2 仍读取到固定假 secret。这个结果不是 profile failure：kernel policy 无法撤回 launcher 已经放进进程环境的字符串。只有 launcher 在 exec 前删除该变量后，SBPL_SANITIZED 才是 0/2 visible。

因此完整 worker contract 必须同时包含：

1. capability isolation；
2. allowlisted/sanitized environment；
3. `--disable-autoexec`；
4. restricted input/output mounts or paths；
5. resource limits and kill/recovery policy。

缺任何一项都不能由其余项推断补齐。

## 攻击与复核

9/9 frozen analyzer attacks 被拒绝：sandboxed outside read/write、loopback、child 的伪成功；缺 worker write；缺 inherited-env 反例；sanitized 后 secret 仍可见；duplicate PID；sandboxed nonce receipt。

独立 audit 重新读取公开 evidence，复算全部 gates 与九个 attacks，得到 `PASS`。artifact SHA-256：

- results：`881e7749d9f237b0c4ca239b1b7a9ff903768ea54ea1f597697fa940ad020d94`
- audit：`95fa648d233c8317bc122ca3e901d5c1f9f3bf56b5f7059fb0eb53d7ac0f7ea2`

## 可以说 / 不能说

可以说：在这台 macOS 26.5.1 主机上，冻结的 deprecated SBPL prototype 对四类受控 capability deny 生效，并保留 Blender trusted probe 的 worker 内写入；环境变量必须由 launcher 另行清理。

不能说：这是受支持的生产 sandbox、最小权限 profile 或未来 macOS 兼容方案。profile 以 `allow default` 为基线；没有测试 parser memory safety、GPU、DoS、全部 filesystem/network/syscalls、IPC、Mach services、devices、真实 secrets 或外网。Apple 的正式 App Sandbox 是 entitlement 与 code-signing 驱动的 kernel control：<https://developer.apple.com/documentation/security/app-sandbox>。

## 下一可证伪边界

不要继续把 deprecated SBPL 扩到“看起来能生产”。下一阶段应冻结 worker backend decision：

- disposable Linux VM/container：可版本化 policy、无宿主 secret、只读资产 mount、单一输出 mount、禁网、PID/内存/CPU/GPU 限额；或
- 自建签名 macOS worker host + App Sandbox inheritance；Blender 作为嵌入 helper 的签名/运行兼容性必须单独验证。

在任一 backend 前，先把 sanitized environment 与 B36 `--disable-autoexec` 写入 launcher contract，并把 failure/recovery 纳入验收。

## 公开 artifacts

- `specs/worker-containment-spec.v0.1.json`
- `experiments/worker-containment-v0-1/results.json`
- `experiments/worker-containment-v0-1/audit.json`
- `blender/probe_b37_worker_containment.py`
