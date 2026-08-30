# AI Native Film Studio：永久引擎仓库就绪协议 v0.1

状态：**在任何 GitHub 仓库创建、fork、首次 push 或 Phase B 源码 mutation 前预注册**

日期：2026-08-30

父 charter commit：`6a38ca3bdd93219ec6dcd001fa72143df7d80a10`

父状态 commit：`58df550d688a7319715ad2ac6015b3f4ff03f02d`

机器合同：`specs/ai-native-studio-repository-readiness.v0.1.json`

## 1. 目的与授权边界

本协议把 post-F0 charter 的 `REPOSITORY_CREATION_AUTHORIZATION` checkpoint 准备成一个可审计、可演练、但**不会创建外部仓库**的决策包。它只允许：

- 读取本机 F0 source checkout、研究仓库和公开 GitHub metadata；
- 在研究仓库外创建可删除的本地 mirror / bare rehearsal remote；
- 向本地 `file://` remote 演练 branch push；
- 在现有研究仓库内提交协议、工具和结果；
- 对候选路径给出 `READY`、`BLOCKED` 或 `REJECTED`。

它不授权 GitHub create/fork/rename、向非本地 remote push、Git LFS 上传、Phase B mutation、DMG 分发、Developer ID 或 notarization 操作。任何 runner 都必须在执行可能写网络的 Git/GitHub 命令前 fail closed。

## 2. 已观察但尚未作为正式结论的输入

正式运行前的只读发现是：

- F0 source HEAD：`fa1b578bb421bbc82b3106b7d4223e11e65fae1d`；tree：`4d761fb73d2b10e051905daedd25cc15da702c27`；
- merge parents：fork `b47eae224b6d3e71559b55df85fd20ae87d3f92b` 与 Blender 5.2.1 target `9e2066aef7ef7e20c142ad7bd3303138a4304c93`；
- 当前 checkout 为 shallow，仅能遍历 1,165 commits，因此不能证明或直接提供完整 Blender 历史；
- HEAD 有 6,671 个 Git LFS paths、815,089,197 bytes，最大单项 27,452,836 bytes；
- HEAD 最大普通 Git blob 为 11,425,316 bytes，低于 GitHub 100 MiB hard block；
- `.git` 约 2.0 GiB，其中普通 objects 约 138 MiB、LFS 约 786 MiB、submodule metadata 约 1.1 GiB；
- 相对固定 upstream target 的产品分支只有 3 个 fork commits 加 1 个 merge commit，tree diff 为 16 paths、841 additions、68 deletions；
- `COPYING` SHA-256 为 `19e6f4b541772f9d7b98a52bdbca3ebd5ef9e404956a9a6de68bfc3c1a178387`，`assets/LICENSE` 为 `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499`；
- 当前 GitHub identity 是 `lovejzzz`，候选 slug `lovejzzz/film-studio-engine` 在只读查询时不存在；这只是候选，不构成 owner/create 授权。

正式 runner 必须独立重测这些值，不能把本节当作结果。

## 3. 两条互斥的仓库拓扑

### R1：`PUBLIC_GITHUB_FORK`

从 GitHub 官方镜像 `blender/blender` 创建 public fork，并请求名称 `film-studio-engine`，随后只把 F0 merge head 接到该 fork 的 Blender commit graph。该路线的目标性质是：

- public fork 的 visibility 不能独立改成 private；
- fork 与 upstream 位于同一 Git object network，避免从 shallow checkout 伪造“完整历史”；
- 未改变的 upstream LFS 仍沿 parent network 获取；F0 修改的两个 LFS branding assets 必须另行验证 push 所需对象与计费归属；
- repository creation 仍需用户明确授权 owner=`lovejzzz`、visibility=`public`、create fork 与首次 source push。

这是当前协议的**建议路线**，但只有正式证据全部通过且用户明确授权后才能执行。

### R2：`PRIVATE_STANDALONE_MIRROR`

创建 private standalone repository，并复制 Blender Git history 与全部所需 Git LFS objects。该路线必须额外证明：

- 来源不是 shallow history；
- bare mirror、`git lfs fetch --all`、Git mirror push 和 `git lfs push --all` 的完整性；
- GitHub repository/LFS storage、bandwidth 与费用被 owner 明确接受；
- destination 不是 fork，且 corresponding-source 和 notices 仍可追踪。

在 owner/visibility/费用未授权、且未完成 all-history LFS inventory 前，此路线的正式状态必须是 `BLOCKED`, 不能用 current checkout 代替。

GitHub 官方边界参考：

- repository size / 100 MiB blob：<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>
- public fork visibility 与 object network：<https://docs.github.com/en/pull-requests/reference/forks>
- Git LFS billing：<https://docs.github.com/en/billing/concepts/product-billing/git-lfs>
- standalone duplication including LFS：<https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository>
- repository limits：<https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/repository-limits>

## 4. 正式输入

固定输入：

- research root：`/Users/mengyingli/Documents/ChatGPT/MyBlenderFilmStudio`；
- F0 source root：`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/blender-v5.2.0-src`；
- external rehearsal root：`/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/repository-readiness-attempt-01`；
- evidence root：`experiments/ai-native-studio-post-f0/repository-readiness-2026-08-30-mac-m2max-attempt-01`；
- source HEAD、tree、parents、dependency commit、charter/spec hashes全部来自机器合同；
- read-only full-history source：`https://github.com/blender/blender.git`；
- candidate GitHub destination：`lovejzzz/film-studio-engine`，只能做不存在性查询；
- local rehearsal destination 必须解析为上述 external rehearsal root 内的 absolute `file://` path。

## 5. Formal stages

### RR.1 Contract and authority admission

复算 parent charter、machine contract、current state 与 source identity。确认外部创建、push、distribution、credentials 和 Phase B mutation 仍为 false。runner 的任何 destination 若是 `http(s)://`、`ssh://`、`git@` 或 GitHub slug，必须在 mutation 前拒绝。

### RR.2 Source, history and remote inventory

记录 shallow 状态、commit/ref/tag counts、source tree、merge parents、remote roster、submodule URLs、Git/LFS/module bytes。官方 remotes 只允许读取。current shallow checkout 必须明确判定为 `NOT_FULL_HISTORY_SOURCE`。

### RR.3 Patch, license, notice and secret surface

相对 `9e2066ae…` 计算 fork-only commits、paths、line surface、LFS changes、普通 blob maximum、`COPYING`/`assets/LICENSE` exact hashes。只扫描 fork-owned textual diff 和即将进入新仓库的新增配置；不得把公开 upstream 历史中的任意文本误报为本项目 secret。扫描至少覆盖 private key header、GitHub token、AWS access key、generic credential URL、password/secret/token assignment。

### RR.4 Read-only full-history acquisition

在 external rehearsal root 获取 GitHub `blender/blender` bare mirror。允许的网络副作用只有 GET/fetch；不得调用 GitHub write API。mirror 必须包含固定 target `9e2066ae…`，且不是 shallow。不得执行 `git lfs fetch --all`，因为这一步只验证建议的 public-fork Git graph；standalone LFS route继续保持 BLOCKED。

### RR.5 Local-only branch graft and push rehearsal

把 local F0 commits fetch 到 full mirror，建立 temporary candidate ref，并 push 到 fresh local bare destination。push 前必须逐项验证 destination protocol、resolved path、空 destination、source exact HEAD 与 authorization sentinel。local destination 的 `main` 必须解析为 `fa1b578b…`，tree与source exact，merge base等于固定 target，fork-owned commits exact为四个。运行 `git fsck --full`；所有外部 remote mutation count 必须为零。

### RR.6 Negative controls

在临时 fixtures 中顺序执行并保留拒绝结果：

1. shallow source 被伪装为 full-history source；
2. source HEAD 与合同不符；
3. non-file destination 或包含 credential 的 URL；
4. destination 非空；
5. 缺失 `COPYING`；
6. fork diff 含 synthetic private key / GitHub token；
7. synthetic ordinary blob 超过 100 MiB；
8. authorization sentinel 试图允许 external create/push。

八项都必须在外部 mutation 前拒绝，且不能污染正式 candidate ref。

### RR.7 Independent audit and topology verdicts

独立 auditor 不 import runner，不信任 runner 汇总字段，直接复算 evidence files、local mirror/destination refs、tree、ancestry、licenses、negative controls 和 network mutation log。输出：

- overall rehearsal：`PASS` / `FAIL` / `BLOCKED`；
- `PUBLIC_GITHUB_FORK`：`READY_FOR_EXPLICIT_AUTHORIZATION` 或拒绝原因；
- `PRIVATE_STANDALONE_MIRROR`：预期保持 `BLOCKED_PENDING_OWNER_VISIBILITY_LFS_COST_AND_FULL_LFS_TRANSFER_AUTHORIZATION`；
- exact next authorization sentence，不得把候选 owner 当成已授权 owner。

## 6. Acceptance gates

正式 PASS 必须同时满足：

1. source HEAD/tree/parents/dependency exact；
2. current checkout被正确识别为 shallow 且未作为 full-history source；
3. read-only mirror非shallow并含固定 Blender target；
4. local `main` 为 exact F0 head/tree，full ancestry可达；
5. fork surface不超过 F0.6冻结的 5,000 non-generated changed lines，当前期望909；
6. HEAD无普通 Git blob达到100 MiB；
7.两份顶层 license binding exact，submodule URLs全为官方 HTTPS；
8. fork-owned secret findings为0；
9. 八项negative controls全拒绝；
10. external repository creates、external Git pushes、LFS uploads、Phase B mutations、DMG distributions、credential reads均为0；
11. independent audit复算通过；
12. formal evidence root immutable且所有 JSON 有 canonical self hash。

## 7. Resource ceiling

- formal开始前free >= 110 GiB；
- projected new local writes <= 5 GiB；
- actual external rehearsal root <= 5 GiB；
- research evidence root <= 8 MiB；
- 最多一次 read-only full Git mirror acquisition；
- 0 Blender starts、0 renders、0 model calls、0 paid API calls；
- 不运行 native build；160 GiB native-build gate因此不适用，100 GiB reserve仍保持。

超限时停止并输出 `BLOCKED_RESOURCE_CEILING`；不得删除任何F0 source、build、DMG或历史证据来制造准入。

## 8. Stop rules

- formal root或external rehearsal root已存在时不覆盖；
- 合同/identity/hash不符立即退出；
- full mirror仍shallow或缺固定target时退出；
- local destination不是fresh absolute `file://` path时退出；
- 发现fork-owned secret、>=100 MiB普通blob或license缺失时退出；
- 任意代码路径准备写GitHub、LFS server或其他network remote时退出；
- 不因public fork路线READY而擅自执行create/fork/push；
- 不把private standalone路线的LFS工作量隐藏在“以后再处理”中。

## 9. 结果的 claim ceiling

即使全部通过，也只证明：在本机、固定commit与固定GitHub公开upstream下，完整Git graph可以被只读取得，F0 branch可以无网络写地接入并推到本地bare remote，且建议的public-fork路线已准备好等待明确授权。它不证明GitHub创建/首次push已发生，不证明private mirror的LFS复制、法律充分性、公开binary发行或Phase B readiness。
