# B36 · Blender 5.2 registered-Text autoexec boundary

日期：2026-08-26（America/New_York）

状态：**`PREREGISTERED_BEFORE_TOOLING_OR_OUTPUT`**

## 可证伪问题

在真实 Blender 5.2.0 LTS 中，同一份包含 `Text.use_module = true` 注册脚本的受控 `.blend`：

1. 使用 `--enable-autoexec` 打开时，是否会执行受控脚本；
2. 使用 `--disable-autoexec` 打开时，是否阻止该脚本；
3. `--factory-startup` 且不传 autoexec override 时，是否保持默认不执行；
4. 在 autoexec 被禁用时，命令行显式指定的 BFS trusted probe 是否仍能运行并检查场景。

只测试“注册 Text 自动执行”这一条边界。它不是恶意文件解析器实验，也不是 OS sandbox 实验。

## 为什么现在测

B10 关闭了真实路径与 symlink 逃逸；B11 能在 append 后识别 drivers、handlers、约束和其他求值结构；B12 只是软 watchdog；B13 绑定了编译收据。仍然缺失的是：主 `.blend` 被 Blender 解析时，内嵌自动脚本能否在任何 BFS 检查前取得 Python 权限。

Blender 5.2 官方手册把 registered Text blocks 与 animation drivers 列为 blend-file 自动执行路径，并说明 Python 本身不限制脚本能力；命令行用 `-y/--enable-autoexec` 与 `-Y/--disable-autoexec` 覆盖偏好。官方依据：

- <https://docs.blender.org/manual/en/5.2/advanced/scripting/security.html>
- <https://docs.blender.org/api/5.2/bpy.types.PreferencesFilePaths.html>

## 受控 canary 与安全边界

测试 `.blend` 由实验工具生成，不来自外部。它只包含一个注册 Text。脚本只允许：

- 从 `BFS_B36_MARKER_PATH` 读取一个明确位于 ignored B36 work 内的目标；
- 从 `BFS_B36_FAKE_SECRET` 读取固定非秘密值 `BFS_B36_NONSECRET_CANARY_V1`；
- 向目标写一个小 JSON，包含自身 PID、固定 token 与 Blender version。

脚本不得联网、创建子进程、读取真实秘密或写出 `experiments/autoexec-boundary-v0-1/work`。runner 在每次启动前 realpath 验证 marker 位于该目录，并要求 marker 不存在。

## 六个独立进程

所有 cell 使用真实 `/Applications/Blender.app/Contents/MacOS/Blender`、`--background`、`--factory-startup`、同一 canary `.blend` 与同一 trusted probe；每个进程上限 60 秒。

| Cell | CLI autoexec 状态 | 冻结预期 |
|---|---|---|
| ENABLE_A / ENABLE_B | `--enable-autoexec` | marker 存在 |
| DISABLE_A / DISABLE_B | `--disable-autoexec` | marker 不存在 |
| FACTORY_DEFAULT_A / B | 不传 override | marker 不存在 |

trusted probe 由命令行显式 `--python` 运行。它只读取场景、记录 PID、registered Text 是否存在、`bpy.app.autoexec_fail` 观察值与 marker 状态，再写 cell report。`autoexec_fail` 值只记录，不作为 gate，因为本实验的因变量是受控 side effect 是否发生。

## 冻结 gate

正式支持必须同时满足：

1. 6 个唯一且为正的 Blender PID；
2. 6/6 exit code 0、无 timeout、trusted probe report 存在；
3. 每次启动前 marker 均不存在；
4. 两个 ENABLE marker 存在，token 精确，marker PID 等于 probe PID；
5. 四个 DISABLE / FACTORY_DEFAULT marker 全部不存在；
6. canary `.blend` 运行前后 SHA-256 字节不变；
7. 七个 frozen analyzer attacks 全部使 analyzer fail：DISABLE 假 marker、DEFAULT 假 marker、ENABLE 缺 marker、token 错、PID 错、重复 PID、source SHA 改变。

## 判决

- `REGISTERED_TEXT_AUTOEXEC_FLAG_BOUNDARY_SUPPORT`：所有 gate 与 attacks 通过；
- `AUTOEXEC_DISABLE_INSUFFICIENT`：任一 DISABLE cell 写出有效 marker；
- `IDENTITY_OR_DESIGN_INVALID`：runtime identity 不符，或 ENABLE cell 没有执行 canary；不允许把“没有执行”解释成保护成立；
- `RUN_INVALID`：timeout、进程失败、trusted probe 缺失、marker preflight 不干净或 source 被修改。

## 明确非结论

即使支持判决成立，也只能说明 CLI flag 阻断了这个注册 Text 自动执行路径。它不能证明解析 `.blend` 是安全的，不能隔离解析器漏洞、内存、文件系统、网络、子进程、GPU、系统调用或真实 secrets；也不覆盖手动 Text 运行、Freestyle、add-ons、包供应链、MCP 权限、签名审批或回滚。

## 披露与下一步

B36 没有人类盲法需求，因此工具、聚合证据、失败与受控 canary 可以公开。任何首次失败必须原样保留。若窄边界成立，下一阶段才可以预注册 OS worker containment；不得把 `--disable-autoexec` 改称 sandbox。

冻结合同：`specs/autoexec-boundary-spec.v0.1.json`
