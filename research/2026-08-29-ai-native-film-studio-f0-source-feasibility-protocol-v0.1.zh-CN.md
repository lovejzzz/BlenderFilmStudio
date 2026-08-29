# AI Native Film Studio：F0 源码可行性预注册 v0.1

- 日期：2026-08-29
- 状态：`PREREGISTERED / NOT STARTED`
- 研究编号：`F0-SOURCE-FEASIBILITY`
- 规范：`specs/ai-native-studio-f0.v0.1.json`
- 产品决策：`ADR-001`
- 研究对象：官方 Blender `v5.2.0`
- 固定提交：`fbe6228777e7d9afefcd61a413844e790ae75db7`
- 目标主机类别：macOS Apple Silicon

## 0. 一句话目的

不是证明“我们能改 Blender”，而是测量：直接拥有 Blender 源码，是否能以可接受的构建、合并、发行和回归成本，换来外部脚本无法可靠提供的电影对象、受控执行和 AI 原生体验。

## 1. 决策背景

Blender 已经提供成熟的数据模型、动画、依赖图、节点、Cycles、EEVEE、合成、色彩管理和 `.blend` 文件生态。我们现有 B01–B62 研究证明，结构化电影意图可以被编译并在真实 Blender 中执行，也证明了准入、收据、恢复、像素、成本和多镜头共享状态可以在有边界的范围内审计。

但现有方式仍有三个结构性摩擦：

1. 用户面对的是通用 DCC 对象和上下文，而不是 Project、Scene、Shot、Character 与 Continuity；
2. Python/operator 边界存在 UI 上下文、生命周期和持久状态限制；
3. AI proposal、diff、approval、budget、job ledger 和 evidence 没有成为应用的原生对象。

源码分叉可能解决这些问题，也可能只制造一套昂贵的换皮和长期合并债务。F0 的任务是证伪其中一个方向。

## 2. 竞争假设

### H-fork

以官方 Blender 5.2.0 为唯一代码基线，维护一个薄分叉，可以在不破坏 `.blend` 兼容和 Blender 专家能力的前提下，提供可测量地更短、更稳定、更可审计的电影工作流；长期合并与 macOS 发行成本低于预注册上限。

### H-shell

原生分叉带来的额外控制不足以抵消构建、合并、GPL 分发、签名、公证和回归成本。一个独立 Film Studio shell 通过版本化协议控制未修改的 Blender，更适合长期产品化。

F0 不允许用“愿景更漂亮”选择 H-fork。只有七道门全部通过，H-fork 才能晋级为正式工程。

## 3. 固定输入

### 3.1 源代码

- 官方仓库：`https://projects.blender.org/blender/blender.git`
- 只读镜像：`https://github.com/blender/blender.git`
- tag：`v5.2.0`
- commit：`fbe6228777e7d9afefcd61a413844e790ae75db7`
- F0.6 merge target：`9e2066aef7ef7e20c142ad7bd3303138a4304c93`

上述两个提交在 2026-08-29 通过官方仓库与官方 GitHub mirror 的 `ls-remote` 交叉确认。后续分支移动不改变本协议。

### 3.2 产品身份

- 研究名称：`Film Studio Engine F0`
- bundle id：`studio.ainativefilm.f0`
- 配置 namespace：`FilmStudioEngineF0`
- Blender 名称只用于说明技术来源与 GPL attribution，不作为用户可见产品品牌。

### 3.3 既有符合性资产

- B01/B02：SceneSpec、BuildPlan、canonical structure；
- B43–B47：Codex structured intent、worker、float pixels、连续序列、production passes；
- B48/B61：质量—成本、真实 Cycles EXR 与解码像素；
- B53–B58：准入、原生 PID、磁盘即时再准入、restart-safe job；
- B60/B62：跨镜头共享状态与真实镜头质量拒绝。

F0 只引用需要的 fixture，不复制或改写历史收据。

## 4. 资源与安全准入

源码、依赖和 build tree 必须在 BlenderFilmStudio 仓库之外。开始任何 clone、dependency fetch、compile、package 或 render 前，立即重算：

- 最低空闲空间：160 GiB；
- 其中不可消费保留：100 GiB；
- F0 初始预测写入：60 GiB；
- 单 gate 最长墙钟时间：12 小时；
- 每个原生进程都必须由本次新鲜准入直接授权；
- 差一字节负控时，不得启动 compiler、Blender 或其他受限原生进程。

`scripts/preflight-f0-source-host.mjs` 是只读初筛，不等价于每次构建的 JIT admission。它不安装软件、不 clone、不修复主机。

## 5. 证据纪律

每个运行使用唯一目录：

```text
experiments/ai-native-studio-f0/F0.<gate>-<utc-date>-<host-id>-attempt-<nn>/
```

每个根至少保存：

- 本次预注册副本与 BlenderFilmStudio Git commit；
- host、OS、CPU、内存、磁盘、Xcode/clang/CMake/Python/Git/Git LFS 身份；Ninja 仅在实际使用时记录；
- 源码 commit、依赖身份与工作目录身份；
- 完整命令、exit code、开始/结束时间；
- 峰值 RSS、写入增量和剩余磁盘；
- stdout/stderr 的完整文件及有界摘要；
- 二进制/包/图像的 hash 或受控外部 artifact URI；
- 独立 audit；
- `PASS`、`FAIL` 或 `BLOCKED` 结论。

失败不删除。修正运行必须创建新 root，并在双方 receipt 中绑定前序 evidence identity。容器 hash 与画面身份分开；EXR 的结论优先使用 decoded pixels 与 pass semantics。

## 6. 七道 Gate

### F0.1：可重复源码构建

在同一 admitted host 上，从两个干净 build root 构建固定提交。两次都必须产出可运行原生应用，并报告 Blender 5.2.0 与固定提交。比较应用 bundle、二进制、资源和运行时自报；字节不同时必须定位到可解释的时间戳、签名或构建路径，不得直接称为“完全复现”。

负控：

- free bytes = required bytes - 1；预期零 compiler/Blender PID；
- checkout HEAD != pinned commit；预期构建前拒绝。

### F0.2：独立身份

只修改达到独立身份所需的最小文件，记录 patch surface。验证名称、bundle id、图标、splash 和配置目录；启动、修改设置、退出和 reset 前后，对官方 Blender 配置做 hash 对照。

这一 gate 不评价 UI 美观，只评价身份与状态隔离。

### F0.3：最小电影工作台

实现 Project / Scene / Shot / Character 四个原生入口和一个明确 Expert Mode。选定一个冻结任务，在官方 Blender 5.2.0 与 F0 build 上分别记录交互数、错误次数和完成时间。至少一个任务必须减少交互，且保存—退出—重开后状态不丢失。

若只是隐藏菜单、重排 workspace，而没有 typed film state，则失败。

### F0.4：合同内嵌

使用同一冻结 SceneSpec fixture：现有外部 compiler 和应用内嵌 compiler 必须生成 canonical-exact BuildPlan bytes。随后在 clean roots 构建 B01/B02。未知字段、路径逃逸、非有限数和未批准 mutation 必须在 scene mutation 前拒绝。

模型不得直接提交任意 Python；它只能产生 versioned typed proposal。

### F0.5：渲染与收据

从批准后的 BuildPlan 无鼠标完成 EEVEE preview 与 Cycles multilayer EXR。验证 process、cost、pixel/pass、failure 和 recovery receipts 的 cross-binding。中断一个 stage 后，只能从已验证 immutable receipt 恢复；篡改 receipt 必须拒绝。

### F0.6：上游合并演练

将 F0 patch 合并到固定后续提交 `9e2066aef7ef7e20c142ad7bd3303138a4304c93`。开始前冻结 merge corpus 与计时方法。

薄分叉上限：

- 手工冲突路径不超过 10 个；
- 人工解决不超过 8 person-hours；
- fork-owned 非生成源码变更不超过 5000 行；
- F0.1–F0.5 的已通过 fixture 不得回归。

任一上限越界，触发 H-shell 建议，不允许通过重新定义“薄”来继续。

### F0.7：安装、卸载与往返

建立 unsigned research package，验证安装和卸载不影响官方 Blender。记录签名/公证的命令、凭证边界与成本，但不在仓库保存秘密。

往返矩阵：

1. 官方 Blender 创建 `.blend` → F0 打开并保存 → 官方 Blender 重开；
2. F0 创建 `.blend` → 官方 Blender 打开；
3. 缺少 Film Studio metadata 时，核心场景仍能打开，并明确降级。

## 7. 总体判定

只有 F0.1–F0.7 全部 `PASS` 且没有 fallback trigger，才建议创建正式 `film-studio-engine` 仓库。此时仍然只证明“值得进入产品原型”，不证明任意电影可以自动生成。

以下任一情况建议 H-shell：

- F0.6 超出冲突、时间或 patch ceiling；
- F0.7 无法实现安全、可解释的独立发行；
- F0.3 没有测得源码介入相对外部 shell 的任务优势；
- F0.4/F0.5 必须扩大 AI 权限或削弱现有安全合同才能工作。

缺少硬件、证书或外部授权时使用 `BLOCKED`，不得伪装为 `FAIL` 或 `PASS`。

## 8. 第一项执行

新机器首先运行：

```sh
node scripts/preflight-f0-source-host.mjs
```

如果接受，先预览再执行源码 bootstrap：

```sh
scripts/bootstrap-f0-blender-source.sh --workspace /absolute/path/to/f0-workspace
scripts/bootstrap-f0-blender-source.sh --workspace /absolute/path/to/f0-workspace --execute
```

F0.1 的正式 runner、receipt schema 与 build commands 应在新主机身份已知后追加为 v0.1 实现，不反向修改这份预注册阈值。

## 9. 依据

1. Blender License: <https://www.blender.org/about/license/>
2. Blender Trademark Policy: <https://www.blender.org/about/trademark-policy/>
3. Official source: <https://projects.blender.org/blender/blender>
4. Building Blender on macOS: <https://developer.blender.org/docs/handbook/building_blender/mac/>
5. Build options: <https://developer.blender.org/docs/handbook/building_blender/options/>
6. Bforartists source: <https://github.com/Bforartists/Bforartists>
7. Full product design: `research/2026-08-29-ai-native-film-studio-design-v0.1.zh-CN.md`
