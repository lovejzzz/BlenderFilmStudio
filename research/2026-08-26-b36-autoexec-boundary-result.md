# B36 · Blender 5.2 registered-Text autoexec boundary result

日期：2026-08-26（America/New_York）

正式判决：**`REGISTERED_TEXT_AUTOEXEC_FLAG_BOUNDARY_SUPPORT`**

边界声明：**`AUTOEXEC CONTROL IS NOT A SANDBOX`**

## 先保留无效尝试

预注册 commit `541e0a7`、spec SHA-256 `45990fd009ce719dfb25b533276b0aab6e3040a2cf9c0a5f0c2f19c90142a170`，工具冻结 commit `76f7402`。

第一次六进程运行的 side-effect 模式符合预期，但 analyzer 把 spec 已冻结的 Blender API version `5.2.0 LTS` 错写成 `5.2.0`，因此 runtime identity gate 为 false，runner 在 attacks 前以 `IDENTITY_OR_DESIGN_INVALID` 停止。无效 artifact 原样保留在 `attempt-1-invalid.json`；只修正这一行字符串比较后，于 commit `0b67163` 重新运行全部进程。

## 真实 Blender 结果

受控 `.blend` 包含一个 `Text.use_module = true` registered Text。脚本只读取固定非秘密 canary 和 ignored work 内 marker path，再写一个 JSON；没有网络、子进程或真实 secret 行为。

| Cell | PID | Marker | `bpy.app.autoexec_fail` | Duration |
|---|---:|---:|---:|---:|
| ENABLE_A | 87507 | yes | false | 489 ms |
| ENABLE_B | 87509 | yes | false | 484 ms |
| DISABLE_A | 87511 | no | true | 489 ms |
| DISABLE_B | 87513 | no | true | 493 ms |
| FACTORY_DEFAULT_A | 87514 | no | true | 496 ms |
| FACTORY_DEFAULT_B | 87517 | no | true | 495 ms |

六个 PID 全部唯一，6/6 exit code 0、无 timeout、trusted probe report 存在。两个 ENABLE marker 的非秘密 token 精确，marker PID 等于 trusted probe PID；四个 DISABLE / FACTORY_DEFAULT marker 均不存在。受控 source `.blend` 前后 SHA-256 都是 `6fa01e9bcd8058d80cd4773926731cee06dc309e35499a69b2df594301f19a18`。

这同时证明两件不同的 measured fact：

1. 当 autoexec 明确 ENABLE 时，一个 registered Text 在 BFS trusted probe 运行前已经取得 Python 执行并完成 side effect；
2. 对这份受控文件，`--disable-autoexec` 与 factory-startup default 都阻断 registered Text，但命令行显式 `--python` 的 trusted probe 仍能运行。

## 攻击与独立复核

7/7 frozen analyzer attacks 被拒绝：DISABLE 假 marker、FACTORY_DEFAULT 假 marker、ENABLE marker 缺失、token 错、marker/probe PID 错、重复 Blender PID、source SHA 改变。

独立 audit 重新读取公开结果和 ignored source，复算 source SHA、全部 gates 与七个 attacks，得到 `PASS`。artifact SHA-256：

- results：`2094bb9ebbee26eaead3d3bf09d5f9ed0198eeee5b6d9f388bdfbd4cb77a60b1`
- audit：`085146099038f2641a1a7b816e6b056a7d7494548e0485e29e00408bdd08c4fc`

## 可以说 / 不能说

可以说：对 B36 的 registered Text 自动执行路径，BFS worker 必须显式传 `--disable-autoexec`，不能依赖用户偏好；trusted CLI probe 在该状态仍可执行。

不能说：`.blend` 因此可安全解析。`--disable-autoexec` 不隔离解析器漏洞、内存、文件系统、网络、子进程、GPU、系统调用、真实 secrets、手动 Text、Freestyle、add-ons、包供应链或 MCP 授权。Blender 官方同样说明 Python 不限制脚本能力，并把 registered Text 与 drivers 列为自动执行路径：<https://docs.blender.org/manual/en/5.2/advanced/scripting/security.html>。

## 下一可证伪边界

把 B36 作为 worker 的一个 fail-closed flag，而不是安全边界。下一阶段应预注册 OS containment canary：在不读取真实秘密、不访问外网的条件下，用 loopback、受控假 secret、工作区外写入和 child-process canary 测试一个实际 worker profile 能否阻断能力；如果 macOS 本机不能提供可审计的 kernel boundary，就记录为平台约束并转向 disposable VM/container，而不是用 watchdog 冒充 sandbox。

## 公开 artifacts

- `experiments/autoexec-boundary-v0-1/attempt-1-invalid.json`
- `experiments/autoexec-boundary-v0-1/results.json`
- `experiments/autoexec-boundary-v0-1/audit.json`
- `specs/autoexec-boundary-spec.v0.1.json`
- `blender/build_b36_autoexec_canary.py`
- `blender/probe_b36_autoexec_state.py`
