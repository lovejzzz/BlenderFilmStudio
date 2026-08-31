# AI Native Studio PB.2 readiness preregistration v0.1

日期：2026-08-31

状态：**readiness-only 已预注册；PB.2 formal execution 未授权、未启动**

机器合同：`specs/ai-native-studio-pb2-readiness-preregistration.v0.1.json`

## 结论

PB.2 不需要从零发明 typed boundary。已接受的 F0.4 证据包含 B01/B02 typed SceneSpec proposal、逐 proposal SHA-256 绑定的 approval、只允许 `COMPILE_BUILD_PLAN` / `WRITE_BUILD_PLAN` 的精确 scope、显式 inspection token 顺序，以及 unknown-field、path-escape、nonfinite 和 unapproved-mutation 四类 mutation 前拒绝。PB.1 又证明当前 public `film-engine` main `4061e12bd45a2bec83e68d0cf49abbf56d4738f6` 可以从完整图构建，并由 C4 关闭独立配置路径。

本预注册只把这些不可变输入交叉绑定到当前仓库身份，并冻结未来 PB.2 的正负例。它没有执行 proposal、没有启动 Blender、没有修改引擎源码或 remote。

## 当前精确输入

- PB.1 接受组合：attempt-04 clean build receipt `fb8bac48…`，binary SHA-256 `4d7f1744…`；C4 runtime receipt `eaabe8c…`、verdict `bc64dd1a…`、accepted audit `f59242af…`。
- 引擎源码：retained attempt-04 source，clean HEAD `4061e12bd45a2bec83e68d0cf49abbf56d4738f6`。
- bounded contract：`film_studio_contract.py` Git blob `3d76aada…`、SHA-256 `73387e41…`；workspace bridge Git blob `bdb18468…`、SHA-256 `6fb3d87f…`。
- F0.4 accepted root：attempt-03，verdict file SHA-256 `2a7d916b…`，verdict self hash `f2888a3b…`，independent audit file SHA-256 `2021acc5…`。
- B01/B02 BuildPlan hash：`316114f1…` / `a9022bf6…`。

## 未来 PB.2 冻结矩阵

两个正例只做 exact proposal + exact approval inspection。八个负例覆盖 rejected、tampered、unapproved、wrong-order、unauthorized-scope，以及继承的 unknown-field、path-escape、nonfinite。

每个负例都必须同时为零：BuildPlan write、Blender start、scene mutation、network call、proposal-originated shell、fresh evidence root 外 filesystem operation、proposal-originated arbitrary Python。任何单项非零即 FAIL，不允许通过重试覆盖。

## 边界

readiness audit 可以读取研究仓库和 retained PB.1 source，并只在新的 readiness evidence root 写一份审计结果。PB.2 formal run、proposal 执行、Blender start、`film-engine` source/ref/tag/release 写入、LFS、签名、公证、DMG 和 PB.3–PB.7 都保持关闭。

本阶段 PASS 只表示输入齐全且 future protocol 已在观察前冻结；它不表示 PB.2 PASS。
