# B34 ignored raw-work cleanup record

日期：2026-08-26（America/New_York）

状态：`RETAINED_AFTER_DELETE_COMMAND_REJECTED`

## 唯一删除目标

`/Users/tianxing/CodexProjects/FilmMaking/Reference/BlenderFilmStudio/experiments/human-quadrature-review-v0-1/work`

不使用 glob，不删除 `experiments/human-quadrature-review-v0-1/evidence/`、`results.json`、spec、protocol、tool source、Git history 或任何其他 experiment。

## 删除前审计

- Git ignore rule：`.gitignore:98` 的 `/experiments/human-quadrature-review-v0-1/work/`；
- allocated size：`4,714,288 KiB`；
- regular files：`3,247`；
- sources：`3,369,144 KiB`；
- composites：`996,728 KiB`；
- display：`162,648 KiB`；
- decoded：`109,844 KiB`；
- carriers：`75,604 KiB`；
- observer-sessions：`288 KiB`；
- attack-response-immutability：`20 KiB`；
- sealed：`12 KiB`；
- filesystem available before deletion：`15,340,596 KiB`。

## 为什么允许删除

B34 的正式 human count 为 0/18，并已因 public carrier-hash join 被标记 `DO_NOT_COLLECT_FORMAL_HUMAN_RESPONSES_FROM_B34_PUBLIC_EVIDENCE_STATE`。因此本地 mappings、sessions 与 raw carrier 不再承担未完成 response 的保管义务。

已提交且不会删除的复现链：

- preregistration：commit `9224bd9`；spec SHA-256 `4afcb29f9d47671d4696d0b6d57f5d7e0c5fde4f08bee1e414040ed480257ba2`；
- package toolchain：commit `432e6b2`；
- independent audits：commits `c981ac0` 与 `00cc6a6`；
- engineering evidence：commit `dbfad5b`；
- public-hash attack tool：commit `78a6aae`；
- superseding finding：commit `c0becd6`；attack evidence SHA-256 `5aa4f88367c383038283c4961e1e7c6545b4aeecef20983328b521002b4077df`。

删除后，raw EXR/PNG/WebM、sealed mappings 与 session packages 不可从本地 trash 恢复；它们只能用上述冻结 scene/runtime/spec/tool 重新计算。提交的 manifests、hashes、独立审计、attack evidence 和研究结论仍在 Git history。

## 事后门槛

删除命令必须只解析为上述绝对目录。完成后要求：目标不存在；`evidence/` 与 `results.json` 仍存在；Git tracked tree 无删除；记录删除后可用空间。若任何门槛失败，状态不得写成完成。

## Action result

第一次且唯一一次删除尝试在执行前被本机安全层拒绝：`rm -rf` 风格命令不被允许。没有文件被删除、移动或修改，目标目录仍完整保留。

没有改用 `find -delete` 等等价绕过。由于当时 filesystem available 为 `15,340,596 KiB`，仍高于 B35 冻结的 `8 GiB` preflight 门槛，处置改为保留 B34 raw work 并继续 B35。若未来确需释放空间，必须建立新的、优先采用可恢复移动或外部归档的记录。
