# Film Engine public fork C1 v0.4 执行授权

状态：**OWNER_AUTHORIZED_PENDING_EXECUTION**

日期：2026-08-30

父修正：`research/2026-08-30-film-engine-public-fork-c1-github-lfs-policy.md`

机器合同：`specs/ai-native-studio-repository-publication-c1-execution.v0.4.json`

## 1. Owner 原文授权

> 我授权在保留 lovejzzz/film-engine public fork、不删除/重建/重命名的前提下，创建一个以 fa1b578bb421bbc82b3106b7d4223e11e65fae1d 为唯一父提交的 publication compatibility commit；只允许修改 .gitattributes、blender_icon_legacy.icns 和 splash.png 三个路径，把两个内容 SHA-256/bytes 不变的品牌资产从 LFS pointer 改为 ordinary Git blob；验证通过后，仅使用 --force-with-lease=refs/heads/main:08bed5b5b42ec017e8dcc87b76f6c373c322b086 更新 main。仍不授权任何 LFS upload、其他 ref/tag、release、签名、公证、DMG 分发或 Phase B mutation。

本文件只版本化这次superseding authorization，不回写v0.3建议或历史失败。

## 2. 唯一允许的提交

新提交的唯一parent必须是`fa1b578bb421bbc82b3106b7d4223e11e65fae1d`，只允许以下三条路径变化：

1. `.gitattributes`只追加两条exact-path override；
2. `release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns`从pointer blob换成ordinary Git blob；
3. `release/datafiles/splash.png`从pointer blob换成ordinary Git blob。

两条override冻结为：

```gitattributes
release/darwin/Blender.app/Contents/Resources/blender_icon_legacy.icns -filter -diff -merge -text
release/datafiles/splash.png -filter -diff -merge -text
```

icon必须保持SHA-256 `be94271b6759adbe6fa7dc96dbce6cf68a371f0212757a4d28667c535586a468`、2,135,147 bytes并形成ordinary blob `497c866c67f1dd5f2ba08ed2ae4c93d5ad1e7256`。splash必须保持SHA-256 `5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf`、565,997 bytes并形成ordinary blob `9af8454bd891d834f10e2ebf072186e567fc7b3e`。

提交只在retained full-history local source的新副本中用Git object/index plumbing生成；不修改shallow F0 checkout，也不改retained repository-readiness bare repository。

## 3. 发布前门

执行前必须再次确认：

- `lovejzzz/film-engine`仍为public `blender/blender` fork、repository id `1351574987`；
- 远端只有`main`，OID exact为`08bed5b5b42ec017e8dcc87b76f6c373c322b086`，0 PR、0 release、0 tag；
- full-history local source non-shallow、162,917 reachable commits、head/tree exact且fsck通过；
- retained F0 checkout clean，两个materialized资产SHA-256和bytes exact；
- research worktree clean，fresh external/evidence roots尚不存在，free disk不低于110 GiB。

候选commit生成后，必须先通过exact parent、exact three-path diff、ordinary blob OID、binary SHA/bytes、attribute unset与fresh `GIT_LFS_SKIP_SMUDGE=1` local clone验证。

## 4. 唯一远端写入

验证全部通过后只允许一次：

```text
--force-with-lease=refs/heads/main:08bed5b5b42ec017e8dcc87b76f6c373c322b086
```

目标只能是`refs/heads/main`，source只能是本次候选commit。push从没有pre-push hook的fresh bare副本执行，并显式绑定empty hooks目录；执行器不得调用任何`git lfs`命令。若lease变化或push失败，立即停止且不重试。

## 5. 验证与禁止项

远端更新后必须以fresh no-smudge remote clone验证两项资产仍直接materialize完整内容，并确认only parent、only three paths、attributes、single branch、0 PR、0 release、0 tag。独立auditor不import runner，复算receipt self hashes、live remote和本地候选对象。

继续禁止LFS upload、任何其他ref/tag、release、fork删除/重建/重命名、standalone replacement、签名、公证、DMG分发和Phase B mutation。任何失败都保留为新attempt，不能覆盖或弱化门槛。
