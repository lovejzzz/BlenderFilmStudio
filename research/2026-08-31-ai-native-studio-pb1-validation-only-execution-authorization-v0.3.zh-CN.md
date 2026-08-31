# PB.1 validation-only 执行授权 v0.3

Date: 2026-08-31

Gate: PB.1 Repository and source identity

Mode: validation-only / no engine source mutation / no engine remote write

## 1. 已授予的精确权限

owner 在当前 Codex 任务中给出以下逐字授权：

> 我授权启动 PB.1 validation-only（Repository and source identity），基线为 lovejzzz/film-engine public fork 的 main=4061e12bd45a2bec83e68d0cf49abbf56d4738f6；允许在机器外部 fresh roots 中进行一次 public engine 只读克隆、一次已有本地 LFS storage 的零网络 materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b 依赖的本地克隆、一次 clean native arm64 build，以及最多两个零渲染产品身份/配置进程；允许把 PB.1 evidence 提交并推送到 BlenderFilmStudio 研究仓库。不得修改 film-engine 源码，不得向 film-engine 写入任何 commit/ref/tag，不得进行 LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

该授权精确满足 v0.2 请求，不扩张为 Phase B 功能开发。

## 2. 双层源码身份

公开验证 HEAD 固定为 C1 publication compatibility commit
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`。它的唯一 parent 必须仍为
F0 产品代码身份 `fa1b578bb421bbc82b3106b7d4223e11e65fae1d`，且只允许 C1
冻结的 `.gitattributes`、icon、splash 三路径差异。除普通 Git blob 发布兼容性外，
C1 不得改变 F0 code/configuration surface。

## 3. 执行顺序

1. 在任何 formal root 前重新检查授权、live fork、研究仓库 clean/pushed、retained
   dependency/LFS storage 和至少 160 GiB free。
2. 运行九项纯负控；任一负控没有在 mutation/start 前拒绝即停止。
3. 只运行一次 `GIT_LFS_SKIP_SMUDGE=1` public engine network clone；禁止 push、tag、
   release 和任何写远端命令。
4. 将 fresh clone 的 LFS storage 只读绑定到 retained local object store，并只运行一次
   `git lfs checkout`。逐项复算全部 materialized path 的 SHA-256/bytes；不得 fetch、pull、
   download 或 upload。
5. 只从 retained clean checkout 做一次 `macos_arm64` 本地 clone，checkout exact
   `a76ef917…`，不得 network fetch。
6. 源码、历史、GPL/notices、generated-path、secret 与依赖门全部 PASS 后，只运行一次
   `/usr/bin/make BUILD_DIR=<fresh-build-root> NPROCS=12`。
7. build 通过后最多运行两个零渲染进程：`--version` 与隔离 HOME 中的
   identity/configuration audit。真实 official Blender configuration root 前后必须逐字节不变。
8. 独立 auditor 不 import runner，复算 receipts、live remote、history、LFS、source、build、
   runtime、资源和零副作用计数；最后才允许提交、push PB.1 evidence。

## 4. 资源与停止规则

- formal mutation 前至少 `171,798,691,840` bytes free；不足时 external root 保持 absent。
- external root 不超过 12 GiB；research evidence 不超过 32 MiB。
- build wall time 不超过 1,200 秒，peak RSS 不超过 4 GiB，同时只允许一个 native job。
- 任一 identity/history/license/dependency/build/runtime/configuration/negative-control mismatch
  写入 fresh immutable failure evidence 并停止；不在同一 root 修复、不降低阈值、不重试 build。

## 5. 仍未授权

`film-engine` 的 source edit/new commit/ref/tag、LFS network transfer、release、签名、公证、
DMG 创建或分发，以及 PB.2–PB.7 全部保持未授权。PB.1 PASS 也只证明这台 admitted
M2 Max 上的 repository/source identity 与 clean build，不证明公开分发、production readiness、
跨平台支持或 autonomous filmmaking。
