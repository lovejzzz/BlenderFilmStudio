# PB.2 C1 tool audit：exclusive delegation correction v0.5.1

Static attempt-01 保留为 `FAIL 15/16`。C1 wrapper 不直接实现 evidence writer，而是调用 exact SHA-bound base runner 的 `write_exclusive`；原审计器只搜索 wrapper 中的 `os.O_EXCL`，因此误报。

修正规则同时要求 wrapper 调用 `base.write_exclusive`、冻结 base runner 含 `os.O_EXCL`、独立 auditor 含 `os.O_EXCL`。不改变 runner、formal scope 或授权边界。
