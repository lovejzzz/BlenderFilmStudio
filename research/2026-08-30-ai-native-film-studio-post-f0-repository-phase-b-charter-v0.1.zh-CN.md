# AI Native Film Studio：Post-F0 仓库与 Phase B Charter v0.1

状态：**在创建/公开永久仓库或开始 Phase B mutation 前预注册**

日期：2026-08-30

机器合同：`specs/ai-native-studio-post-f0-phase-b.v0.1.json`

父研究提交：`463d76f0325223430c00ab7ea1a8fd167db7392a`

## 1. 决策

F0.1–F0.7 已全部 PASS，冻结协议中没有 fallback trigger。当前证据支持把 direct official-Blender thin fork 推进到**有界产品原型**，不支持把它描述成公开发行、production-ready、跨平台、任意电影自动生成或法律充分。

下一阶段不是 F0.8。它是一个新的 Phase B 合同：先把永久源码仓库、许可证/发布边界和 B01/B02 + B62 垂直切片写清楚，再获得创建/公开仓库的明确授权。

## 2. 授权边界

本 charter 可以提交到现有研究仓库。它**不授权**：

- 创建或公开新的 GitHub 仓库；
- 把 Blender 源码历史推送到新 remote；
- 开始 Phase B 产品源码 mutation；
- 创建、读取或上传 Developer ID / notarization 凭证；
- 分发 F0.7 unsigned DMG。

下一项所需权限必须明确给出 repository owner、visibility，以及是否允许创建和首次 push。没有这些信息时停在 charter，不猜测。

## 3. F0 冻结输入

机器合同逐一绑定七份 accepted verdict、15 份 retained `BLOCKED` / `FAIL` verdict 的文件 SHA-256。accepted self hashes 为：

| Gate | Accepted root | Receipt / verdict self hash |
|---|---|---|
| F0.1 | attempt-07 | `f4a18aec803a09d2c149222312a8e9f507d1103f95273951af79acaf04ba62cb` |
| F0.2 | attempt-02 | `615c3021227a4f3b4008ec73acca5ddc04511e3283dfc1a7bb7fddfde45192f4` |
| F0.3 | attempt-01 | `472abf5df3c66dba375e46fe7e9a0e152cc3d6c37966ab13f6d7e2601fea0390` |
| F0.4 | attempt-03 | `f2888a3b4c89df3370c13fbf28097ecb4d83a3f11f325588a12321d27f7666a3` |
| F0.5 | attempt-02 | `a85a2d64bb080b89051986ad83b6489317909a6f0b7ad75b5c194a252a375e71` |
| F0.6 | attempt-03 | `e67b9b942f772b9aef096c4b5cd988dfac7be2e1a3bfec7ad5a28a51111693d3` |
| F0.7 | attempt-05 | `626ea953fefd6fb1b8c3044248c653c7ce0cbc18a69a2e8eff5bb37e78a2d94a` |

这些输入不能被 Phase B 重算成新的历史。Phase B 只能导入、交叉绑定并在新 evidence root 中做回归。

## 4. 拟议仓库边界

永久引擎仓库拟用 slug `film-studio-engine`；owner 和 visibility 等待明确授权。

- 初始源码身份：Blender 5.2.1 LTS merge commit `fa1b578bb421bbc82b3106b7d4223e11e65fae1d`，dependency commit `a76ef917b4849ba2b1b1deb1a643e131a884a63b`。
- 保留完整 Blender Git 历史；官方 `https://projects.blender.org/blender/blender.git` 作为只用于 fetch/merge 的 upstream。
- 产品身份继续是 `Film Studio Engine F0`、bundle id `studio.ainativefilm.f0`、configuration namespace `FilmStudioEngineF0`，直到另一个版本化品牌决策改变它。
- 引擎仓库只放源码、构建定义、测试和许可证材料；不提交 build tree、`.app`、DMG、缓存或研究 evidence corpus。
- `BlenderFilmStudio` 继续保存协议、实验、收据和公开研究站点；control plane 暂不拆成新仓库。

## 5. GPL、商标与发布

- 保留 Blender GPL 文件、版权和第三方 notices；每个对外分发的修改版 binary 都必须有可验证的 corresponding source 路径。
- 使用独立产品名称和资产；“Based on Blender”只能是事实性归属，不能成为主品牌。
- F0.7 的 ad-hoc-signed DMG 只是本机研究包。没有 Developer ID、notarization、Gatekeeper acceptance、source/notices audit 时，不发布 macOS binary。
- 凭证只允许通过明确的本机/CI secret boundary 使用，不进入 Git、receipt 正文或聊天复制。
- 这些是工程政策，不替代专业法律意见。

## 6. Phase B 七道门

### PB.1 Repository and source identity

在获批的新仓库中保留完整上游历史，HEAD 从 `fa1b578bb421…` 起步；复算F0 patch identity、独立品牌和clean native build。Git 中不得出现生成产品。

### PB.2 Typed proposal and approval boundary

B01/B02 必须以 typed SceneSpec proposal 进入。未批准、篡改、越权或错误顺序的 proposal 在 Blender mutation 前拒绝；模型没有 unrestricted `bpy`、shell 或 filesystem 权限。

### PB.3 Canonical compile and editable workspace

批准后的 B01/B02 产生 canonical-exact BuildPlan 与正确分层的 semantic/provenance identity。Project / Scene / Shot / Character 状态持久化，Expert Mode 往返继续 lossless。

### PB.4 Preview, final and receipts

产品完成冻结的 EEVEE preview 与 Cycles multilayer EXR，生成 process、pixel、pass、cost、failure receipts，并由独立进程重新审计。不得以 UI “完成”替代可复算事实。

### PB.5 Restart-safe job control

受控中断后只恢复未完成 immutable stage。stale/forged/out-of-budget receipts 在 additional Blender work 前 fail-closed。

### PB.6 B62 three-shot vertical slice

wide / medium / close 保持非摄影机共享状态，生成可观看三镜头输出。frame 288 的冻结构图拒绝继续保留；产品可以显示并支持人类修订，不能自动放宽阈值制造 PASS。

### PB.7 Human review and bounded verdict

机器 gate 与延迟披露的人审都进入证据。最终只有 `PASS` / `FAIL` / `BLOCKED`；即使 PASS，也只关闭这一个垂直切片，不扩写成任意电影或生产发行结论。

## 7. 资源与安全

- native build 前至少 160 GiB free；任何 native mutation 前重新满足100 GiB reserve加全部projected writes。
- Blender source/build继续在研究仓库外；正式 evidence root immutable，失败全部保留。
- 不因新仓库而降低 F0.1–F0.7 regression、B53–B59 admission/recovery 或 B62 human boundary。
- `AGENTS.md` 的 in-app browser crash guard 继续生效。
- 0 secrets in repository；0 unrestricted model execution authority。

## 8. Stop rules

以下任一条件立即停止对应动作：

1. 未明确授权 repository owner / visibility / create / first push；
2. full-history source identity、GPL/notices 或独立品牌不能保持；
3. thin-fork ceiling 或任一 F0 regression 失败；
4. public binary 缺少 Developer ID、notarization、Gatekeeper、corresponding source 或 notices audit；
5. 为让 B62 或 Phase B 通过而事后放宽阈值；
6. 把跨平台、marketplace、多人协作或生成式资产扩张塞进本垂直切片。

若 thin fork 不再满足冻结上限，架构回退到 external Film Studio shell + unmodified Blender，而不是继续扩大 fork。

## 9. 下一项原子动作

先提交并推送本 charter 与机器合同，使其获得不可歧义的 preregistration commit。之后停止在新仓库创建之前，等待明确的 owner / visibility / create / first-push 授权。
