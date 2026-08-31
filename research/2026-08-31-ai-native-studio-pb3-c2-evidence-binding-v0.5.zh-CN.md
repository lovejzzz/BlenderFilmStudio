# PB.3 validation-only C2：授权与证据绑定 v0.5

日期：2026-08-31
状态：`PASS_STATIC_29_OF_29_INERT`
正式 PB.3 work/evidence roots：不存在
Blender start / proposal execution / BuildPlan write / render：`0 / 0 / 0 / 0`

## 完成性审计结论

C1 已正确执行 2 GiB / 64 MiB 容量上限、exclusive log writes 和 symlink rejection，但继续审计未来正式路径时发现三个未被独立证明的条件：

1. base runner 只要求授权文字包含 `PB.3`，没有把 execution contract 绑定到冻结授权请求的逐字正文和 SHA-256；
2. independent auditor 从 receipt 读取 work/evidence roots，却没有证明它们就是 `execution.authorizedRun` 的 exact roots；
3. independent auditor 只检查 process count、exit zero 与 offline flags，没有独立重建四组 exact argv，也没有读取并重哈希八份 stdout/stderr logs。

这些都是正式执行前的工具缺口。正式 roots 从未创建、Blender 从未启动，因此没有 PB.3 结果被污染；v0.2 和 C1 静态证据继续保留。

## C2 校正

C2 runner 在调用冻结的 C1/base runner 前新增以下 fail-closed gate：

- execution 必须绑定 C2 correction 和冻结的 C2 authorization request；
- user authorization text 必须逐字等于 request，并绑定其 SHA-256、明确 PB.3 scope 和授权时间；
- execution commit 相对其唯一父提交只能改变 execution contract 一个路径；
- authorization request 和 C2 correction 的 exact bytes 必须已存在于 execution parent；
- repository/source/binary/work/evidence 五个 arguments 必须等于 `authorizedRun`；
- C1 PASS 后重建四组 exact argv，读取并核对八份日志 SHA-256。

C2 independent auditor 先运行冻结的 C1/base 独立审计，再独立复核上述 binding，并生成 work root 与 pre-C2-audit evidence root 的 regular-file count、bytes 和 canonical manifest SHA-256。最终 C2 audit 自身在写入前纳入 64 MiB projection，并在写后复算 final evidence bytes。

## 冻结产物与验证

- C2 correction：`specs/ai-native-studio-pb3-validation-tool-c2-evidence-binding.v0.5.json`
  - SHA-256：`55642b2d549811ef35bcda3b91c941a0584d1698d3354de842a426de04990cec`
- C2 runner：`scripts/run-ai-native-studio-pb3-validation-c2.py`
  - SHA-256：`f7384b59178cb8d312800108ce614c05cf1ba8fa89840667e3a95a7bf947f31b`
- C2 independent auditor：`scripts/audit-ai-native-studio-pb3-validation-c2.py`
  - SHA-256：`e2af556008ea2426e3b86d443f1dcc202ff2455215a4c4f9d94b836a88242e72`
- C2 static auditor：`scripts/audit-ai-native-studio-pb3-tool-freeze-c2.py`
  - SHA-256：`97d7c45b5b04f1ab84c9de74a88b77c613600b98220abd6c604229c192b97d51`
- inert template：`specs/ai-native-studio-pb3-validation-execution-c2-template.v0.5.json`
  - SHA-256：`efab947ac9b8730e5118faf4b29891d68dada47c7be7365e8494af3f88e785d7`
- exact authorization request：`specs/ai-native-studio-pb3-validation-only-authorization-request-c2.v0.4.json`
  - SHA-256：`44e52a5619967d79e26258ebfcc123a28401f69afc05159174f2b911a4a963ab`
- static audit：`experiments/ai-native-studio-phase-b/PB.3-c2-tool-freeze-2026-08-31-mac-m2max-attempt-01/audit.json`
  - file SHA-256：`94a0fc4d3131e12bf32021d8f7c02e55ef300c14293d65ce8cee67deaa4b5c88`
  - audit self hash：`f7babc9e28ed37ed53bdaff43e2cad0dbbf735e653c0fa614bf565960c2adffb`
  - verdict：`PASS 29/29`

额外纯函数负控证明 runner 与 auditor 为 B01/B02 build/reopen 重建的四组 argv 完全一致，并确认 manifest 对 root symlink 与 descendant symlink 都会拒绝。

## 权限边界

C2 没有创建正式 PB.3 root，没有启动 Blender，没有执行 proposal 或写 BuildPlan。它不把 template、一般性的继续指令或先前 PB.2 权限变成 PB.3 authority。

未来正式 attempt-01 只能在用户明确批准
`specs/ai-native-studio-pb3-validation-only-authorization-request-c2.v0.4.json`
中的 exact text 后，通过一个新的、单路径、不可变 execution contract 启动。PB.4–PB.7、film-engine mutation、network、render、签名、公证和 DMG 继续为零权限。
