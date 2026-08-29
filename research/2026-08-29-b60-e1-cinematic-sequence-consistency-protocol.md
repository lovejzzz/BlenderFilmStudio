# B60-E1：电影序列确定编译与共享状态一致性协议 v0.1

日期：2026-08-29

状态：**正式实验前预注册**

机器：当前 Codex 宿主机

运行时：`Blender 5.2.0 LTS / fbe6228777e7`

## 1. 研究问题

已关闭的 B58 证明单镜头 production compiler 可以被持久化编排、恢复并审计，但它没有证明三个镜头之间的人物、表演、场景和光影不会漂移。B60-E1 询问：当摄影机按预先声明的 wide / medium / close 方案变化时，同一结构化电影意图能否由已准入的 production compiler 在六个独立真实 Blender 进程中产生可重复且共享状态完全一致的场景？

## 2. 可证伪假设

若工作流具备跨镜头确定编译能力，则：

1. 三份 SceneSpec 各自连续生成两次 canonical BuildPlan 时字节完全一致；
2. 每份 SceneSpec 的两次独立 production compile 产生相同的 canonical scene structure；
3. 六份 BuildPlan 的 actor、asset、target、light、world、去除 `outputRoot` 后的 render、outputSpec 与 security 投影完全一致；
4. 六份 scene structure 的 actor、asset collection、target、render 与非 CAMERA managed object 投影完全一致；
5. 三类摄影机参数与预注册值逐字段一致、两次重复相同、三类镜头彼此不同；
6. 任意一个已冻结身份、骨架、拓扑、形态键、灯光、目标、输出或摄影机契约被篡改时，独立验证器都会拒绝；
7. 全过程只进行场景编译，不渲染任何像素，不调用模型、网络或 Docker。

任一条件失败，正式结论必须是 `CINEMATIC_SEQUENCE_CONSISTENCY_NOT_SUPPORTED`，不得改阈值补救。

## 3. 固定输入

机器可读协议：`specs/cinematic-sequence-consistency.v0.1.json`。

三份镜头输入：

- `specs/benchmarks/B60-wide.scene.json`：`SHOT_6001`，40 mm；
- `specs/benchmarks/B60-medium.scene.json`：`SHOT_6002`，72 mm；
- `specs/benchmarks/B60-close.scene.json`：`SHOT_6003`，100 mm。

三者必须继续绑定同一 `B03.actor.json`、`B03-lead.blend` 与 `body-idle.blend`。ActorSpec、人物资产、动作文件、三份 SceneSpec、production release 与 expected PlanHash 的 SHA-256 均在机器可读协议中冻结。

允许变化只有 `shot.id`、`shot.title`、`shot.activeCamera`、`cameras`、`render.outputRoot` 与 `outputs.root`。镜头 seed、帧域、资产、ActorSpec、表演、targets、lights、world、除输出目录外的 render、outputSpec 和 security 不得变化。

## 4. 正式两阶段运行

### 4.1 预检阶段

预注册 commit 必须先推送到 `origin/main`，并且三个正式根均不存在。预检工具随后：

1. 重开协议、三份 SceneSpec、ActorSpec、人物与动作资产并验证哈希；
2. 对三份 SceneSpec 各编译两次 BuildPlan，要求 canonical bytes 与 expected PlanHash exact；
3. 验证共享投影和允许变化集合；
4. 运行六次 production preflight；
5. 写入 self-hashed outer preflight receipt，记录 Blender/render/model/network/Docker 全零。

预检 evidence 必须单独提交并推送，formal runner 只能绑定该 exact commit。

### 4.2 正式阶段

正式 runner 创建 fresh/disjoint attempt 与 formal roots，按 `WIDE-A/B`、`MEDIUM-A/B`、`CLOSE-A/B` 顺序调用已准入的 `run-production-blender-compile.mjs`。每个 case 使用独立的 preflight、attempt 与 output root。预注册上限为六次 production compiler invocation 和六次 native compile Blender start；不得渲染。

runner 完成后调用独立 auditor。auditor 不信任 runner 汇总，必须从磁盘重开所有 production receipt、build plan、scene manifest、canonical structure、budget report 与 compile receipt，验证文件 SHA/self-hash、输入绑定、A/B 重复、跨镜头共享投影、摄影机差异和资源计数。

## 5. 十个负控攻击

独立 auditor 必须在内存深拷贝权威证据，每次只改变一个字段并要求验证失败：人物资产 SHA、ActorSpec SHA、identityLock、rest pose SHA、mesh topology SHA、shape-key-set SHA、灯光能量、target transform、output profile，以及未注册摄影机参数。负控不允许修改磁盘上的正式证据，也不允许启动 Blender。

## 6. 预注册时不存在的工具与输出

以下 candidate tools 在本协议提交时必须不存在，防止先看正式结果再写验证器：

- `scripts/preflight-b60-e1-cinematic-sequence-consistency.mjs`
- `scripts/run-b60-e1-cinematic-sequence-consistency.mjs`
- `scripts/audit-b60-e1-cinematic-sequence-consistency.mjs`

以下正式根在本协议提交时必须不存在：

- `experiments/cinematic-sequence-consistency-preflight-v0-1`
- `experiments/cinematic-sequence-consistency-attempt-v0-1`
- `experiments/cinematic-sequence-consistency-v0-1`

## 7. 结论边界

B60-E1 即使通过，也只支持“结构化输入可确定编译，并在有意改变摄影机时保持人物/场景/光影共享状态”。它不支持 `.blend` 容器字节确定、渲染像素复现、时间连续性、电影感、真人偏好或成本结论。下一道实验必须实际渲染 EXR 才能触及这些主张。
