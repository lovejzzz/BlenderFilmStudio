# AI Native Film Studio PB.1 validation-only 授权请求 v0.2

状态：**BLOCKED_AWAITING_EXPLICIT_OWNER_AUTHORIZATION**

日期：2026-08-30

父charter：`research/2026-08-30-ai-native-film-studio-post-f0-repository-phase-b-charter-v0.1.zh-CN.md`

机器合同：`specs/ai-native-studio-pb1-validation-only-authorization-request.v0.2.json`

## 1. 为什么需要v0.2

Phase B v0.1在永久仓库创建前冻结，PB.1写的是“HEAD从`fa1b578b…`起步”。仓库创建后，GitHub public-fork LFS policy阻止两个品牌对象；随后owner独立授权C1，使live `main`成为`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`。该commit唯一parent仍是`fa1b578b…`，只改变`.gitattributes`、icon、splash，F0代码路径变化为0，独立审计59/59 PASS。

因此PB.1不能假装live HEAD仍是`fa1b…`，也不能回写v0.1。v0.2只修正PB.1 validation baseline：

- publication provenance HEAD：`4061e12b…`；
- F0 product-code identity parent：`fa1b578b…`；
- C1 compatibility surface：exact three paths；
- merge base：`9e2066ae…`；
- reachable / fork commits：162,918 / 5。

## 2. 推荐的最小首步

推荐先做**PB.1 validation-only**，不做产品功能开发。它回答四个问题：

1. GitHub public fork是否真的保留完整Blender历史和exact C1 main；
2. 除C1三路径外，F0 code/config tree是否与`fa1b…`一致；
3. GPL/notices、独立品牌、依赖和0 generated products in Git是否仍成立；
4. 在fresh external source/build roots中能否完成一次clean native arm64 build，并由最多两个零渲染进程报告正确产品身份和隔离配置。

这不是PB.2，也不允许修改引擎源码。任何失败都是PB.1的有效结果。

## 3. 冻结输入与门槛

- repo：public `lovejzzz/film-engine` fork，repository id `1351574987`，parent `blender/blender`；
- only remote head：`refs/heads/main=4061e12b…`；0 tag、0 PR、0 release；
- tree / sole parent：`5f0cb3eb…` / `fa1b578b…`；
- C1 ordinary blobs：icon `497c866c…`、splash `9af8454b…`，SHA-256/bytes exact；
- dependency：local clean `macos_arm64` commit `a76ef917…`；
- retained LFS inventory：6,671 paths、815,089,197 content bytes、6,671 locally downloaded paths；只允许复用已有本地storage，网络download/upload均0；
- license/notices：`COPYING`、`assets/LICENSE`和19-path notice inventory exact；
- build：一次`/usr/bin/make BUILD_DIR=<fresh> NPROCS=12`，fresh out-of-source root，最长1,200秒、peak RSS不超过4 GiB；
- resource admission：formal mutation前至少160 GiB free；external/evidence ceilings为12 GiB / 32 MiB；
- runtime：最多2个产品starts、0 render、最大并发1；期待`Film Studio Engine F0`、5.2.1 LTS、build hash prefix `4061e12bd45a`、bundle id `studio.ainativefilm.f0`、namespace `FilmStudioEngineF0`。

## 4. 允许与禁止

获得明确授权后才允许：一次public engine只读clone、一次从已有本地LFS storage materialize、一次本地dependency clone、一次native build、最多两个零渲染产品进程，以及向`BlenderFilmStudio`研究仓库写入/推送PB.1 evidence。

仍禁止：

- 修改`film-engine`任何源码或创建新engine commit；
- 更新`film-engine`任何ref/tag；
- LFS upload或network download；
- release、签名、公证、DMG创建/分发；
- PB.2–PB.7；
- unrestricted model `bpy`/shell/filesystem authority。

九项负控必须在相应mutation前拒绝wrong HEAD、shallow history、license漂移、tracked generated product、dependency mismatch、dirty source、remote/LFS network write、insufficient disk和product/config identity drift。失败使用fresh immutable evidence root，不原地修复或降低阈值。

## 5. 需要owner明确回复的授权句

> 我授权启动 PB.1 validation-only（Repository and source identity），基线为 lovejzzz/film-engine public fork 的 main=4061e12bd45a2bec83e68d0cf49abbf56d4738f6；允许在机器外部 fresh roots 中进行一次 public engine 只读克隆、一次已有本地 LFS storage 的零网络 materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b 依赖的本地克隆、一次 clean native arm64 build，以及最多两个零渲染产品身份/配置进程；允许把 PB.1 evidence 提交并推送到 BlenderFilmStudio 研究仓库。不得修改 film-engine 源码，不得向 film-engine 写入任何 commit/ref/tag，不得进行 LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

一般“继续”“开始Phase B”或先前C1授权都不满足这个门。没有上述等价的明确范围时，停在本请求。
