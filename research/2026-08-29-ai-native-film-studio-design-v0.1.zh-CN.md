# AI Native Film Studio 设计文档 v0.1

日期：2026-08-29  
状态：方向已采纳；实现尚未准入  
决策编号：ADR-001  
研究仓库：BlenderFilmStudio

## 0. 执行结论

BlenderFilmStudio 的长期方向从“让 AI 操作通用 Blender 界面”升级为：

> 以 Blender 官方开源代码为图形、动画、求值和渲染内核，制作一个独立品牌、GPL 合规、AI 原生、以镜头和电影语义为第一对象的新桌面软件。

该项目不是从零重写三维引擎，也不是给 Blender 增加聊天侧栏。它把已经验证的 `SceneSpec → immutable BuildPlan → admission → Blender → receipt → audit` 研究链植入一个新的产品控制面，让 AI 提交可检查、可撤销、可恢复的结构化电影意图，由确定性内核执行。

推荐采用“薄内核分叉 + 独立 AI 控制面”的混合架构：

- **GPL Engine Distribution**：基于 Blender 官方稳定分支，包含自定义电影工作区、有限原生操作、SceneSpec 编译器、任务执行器和 Blender 集成；公开对应源代码。
- **AI Control Plane**：Codex CLI、本地模型或远程模型服务负责理解、提案和规划，经版本化协议与引擎通信；不把任意模型输出当作可执行代码。
- **Conformance Suite**：当前 B01–B62 的规格、失败样例、攻击、收据、像素和成本实验成为新软件的符合性测试，而不是被废弃的旧原型。

在完成源码构建、重品牌、最小原生编辑器、协议内嵌、上游合并和安装包六项可行性实验之前，不把“做自己的软件”描述为已完成能力。

## 1. 为什么改变方向

### 1.1 现有方式的结构性问题

通过界面自动化控制 Blender 会引入不属于电影问题本身的脆弱性：焦点、窗口、上下文、面板状态、快捷键、弹窗和应用生命周期。即使改用 `bpy` 或后台进程，用户仍面对 Blender 的通用对象模型与庞大界面，而不是项目、场次、镜头、人物、表演和连续性。

我们需要的控制权不是“更多按钮”，而是：

- 在数据进入求值图之前验证它；
- 把角色、镜头、接触、灯光意图设为一等数据；
- 把 AI 的每次修改表达为计划和差异；
- 控制进程、资源、缓存、恢复和证据写入；
- 只暴露与当前电影任务相关的界面；
- 必要时进入 C/C++ 层补充稳定接口，而不是依赖 UI 上下文。

### 1.2 为什么不从零开发

Blender 已经提供成熟的数据块、依赖图、动画、约束、节点、模拟、色彩管理、Cycles、EEVEE、合成、视频、文件兼容和跨平台基础。重写这些能力会把项目从“电影软件设计”变成长期图形基础设施工程。

直接使用 Blender 源码意味着我们继承成熟引擎，也继承大型 C/C++ 工程、跨平台构建、GPU 后端和持续上游合并责任。因此设计目标是最小化核心分叉面，而不是最大化改动量。

### 1.3 Bforartists 给出的证据

Bforartists 是 Blender 的完整 fork，保持 `.blend` 兼容和完整 3D pipeline，同时重组界面与工作流。它证明“基于 Blender 做独立发行版”在工程上成立；但它的主要问题仍是人工 DCC 易用性，不是 AI 原生电影语义。因此本项目应直接跟踪 Blender 官方上游，把 Bforartists 作为 UI 分叉和维护策略的研究样本，而不是再增加一层永久上游依赖。

## 2. 产品定义

### 2.1 产品使命

把导演、摄影、美术和动画意图编译成可编辑、可验证、可重复渲染的三维镜头，并让人始终保有决策权。

### 2.2 核心用户

1. 独立导演和小型团队：希望用有限预算制作一致、可修改的多镜头影像。
2. 预演、动画和虚拟制作人员：希望把剧本、分镜和参考图快速转成可靠场景。
3. 技术导演与 TD：希望获得可审计的场景编译、批处理、恢复和渲染基础设施。
4. 研究人员：希望在冻结协议下比较模型、资产、摄影与渲染策略。

### 2.3 第一阶段工作任务

用户给出剧本片段、角色圣经、资产和视觉参考；系统生成场次与镜头提案。用户选择并锁定意图后，系统编译角色、环境、表演、摄影机、灯光和输出合同，制作低成本 animatic，运行机器检查和人工审片，再选择性地生成 Cycles EXR 与交付视频。每一步可恢复、可重放、可解释其成本。

### 2.4 非目标

- 不承诺一句话自动生成完整长片。
- 不从零重写建模、动画或路径追踪引擎。
- 不让模型任意执行 Python、shell 或插件代码。
- 不以像素哈希、单一感知指标或“有输出”替代电影质量判断。
- 不假定任意 AI 生成人物已经可用于真人近景。
- 不把隐藏 Blender 面板称为 AI 原生设计。
- 不在可行性实验前删除 Blender Expert Mode。

## 3. 从既有研究继承什么

### 3.1 结构化电影编译器

- SceneSpec 已覆盖输出、资产、角色、目标、接触、抓握、轨迹、相机、灯光和安全边界。
- B01/B02 的独立净构建证明 canonical BuildPlan 与 canonical scene structure 可以一致；`.blend` 容器字节并不稳定，因此不能作为语义身份。
- B43 证明 Codex 订阅环境在冻结输入上可以生成与 oracle canonical exact 的结构化意图，且不需要生成式视频模型。
- B44 将该意图通过 Linux worker 编译为可复现结构；拒绝样本在容器启动前停止。
- B60 在真实 Blender 5.2 中对 wide、medium、close 三镜头各运行两次，六次编译全部通过，共享人物、表演、场景、灯光和非摄影机状态一致。

产品结论：`SceneSpec` 和 `BuildPlan` 应成为软件内部持久 API，而不是临时脚本输入。

### 3.2 角色、动作与交互

- ActorSpec、真实 rig、Shape Keys、眼神目标、脚底接触、父级切换、刚性间距、双指 IK 和轨迹回放已经进入实验编译链。
- 源刚体求解的跨运行精确复现曾失败；冻结 132 帧轨迹可零误差回放。
- 这些结果支持“明确约束的角色技术底座”，不支持电影级皮肤、毛发、口腔、微表演或任意复杂接触。

产品结论：人物身份、姿态层、表演层、接触事件和 corrective pass 必须分层，并在界面中可单独覆盖。

### 3.3 安全、准入与执行证据

- 路径逃逸、隐藏资产求值、autoexec、环境变量泄漏、资源超限和日志截断均产生过真实反例并被保留。
- B36 证明 `--disable-autoexec` 能阻止 registered Text 自动执行，但它不是完整 sandbox。
- B37 证明旧 macOS SBPL canary 可阻断窄能力，同时也证明继承环境可泄漏秘密；生产系统不能依赖 deprecated sandbox。
- B53–B57 建立从总路径准入、原生 child PID、生产入口到 native spawn 前磁盘即时再准入的链；B57 最终通过 26/26 gates、56/56 attacks，并证明差一字节时 Blender 零启动。
- B58 建立耐久 job manifest、stage receipt、失败保留、重试 root 和独立再审计，证明单镜头编排可以从证据状态恢复。
- B59 关闭宿主机容量与稳定性 Gate 0，并留下容量 sentinel 与恢复路径。

产品结论：AI 不能直接调用 Blender；所有改变必须经过“提案—验证—准入—执行—收据—审计”状态机。

### 3.4 像素、渲染与成本

- B45 在独立真实 worker 中获得两组解码 float pixels exact；B46 将其扩展到跨构建连续 8 帧，并验证失败 root 不得晋级。
- B47 验证 Combined、Depth、Normal、Vector 和 Cryptomatte 等生产通道的解码像素可复现；EXR 容器字节不必相同。
- B48 的正式质量—成本留出实验中，只有 128 spp raw 同时通过两个场景的三项冻结质量门；OIDN 在不同目标上存在权衡。
- B49 测得渲染时间近似随像素数线性增长，并分别验证 motion blur 与 depth of field 的数值语义；艺术意图仍需人审。
- B51 证明 native CPU 显著快于 qemu worker，Metal warm path 更快，但 CPU/Metal 数据与 beauty 不能直接共享 exact contract；随后建立按 pass 分流和 byte-exact 重组原型。
- B52 系列建立真实 multipart EXR 的 typed float32 adapter、时序累积、量化恢复、投影深度与运动风险研究，同时保留多个被正式拒绝的泛化假设。
- B61 在同机、同 Blender build、固定 CPU/Cycles/OCIO/seed 下，9/9 关键帧 A/B 解码 Combined 像素 exact；实测 1920×1080、64 spp 的 18 帧 render operator 均值为 6.084 秒/帧，峰值 RSS 约 4.5 GB。
- B62 Phase 0 生成三份资产库、动作库、12 秒/288 帧/三镜头场景、完整 EEVEE animatic 和三张 1080p Cycles 校准帧；随后 camera holdout 在技术门通过后仍因 frame 288 构图超过冻结阈值而科学拒绝。

产品结论：渲染设置必须是版本化 profile；像素身份以解码数组和语义通道定义；机器技术通过与人工艺术通过必须分开显示。

### 3.5 研究方法本身

现有实验已经形成可直接产品化的纪律：运行前冻结假设和阈值；输出写入唯一 immutable root；失败不可覆盖；correction 必须绑定旧失败；正式结果由不导入生产 runner 的 auditor 重放；磁盘、进程、内存、时间和文件均进入收据。

产品结论：Journal、failure tree 和 evidence explorer 不是调试附属物，而是 AI 原生软件的核心用户体验。

## 4. 产品原则

1. **电影对象优先**：项目、场次、镜头、人物、表演、连续性和交付优先于 Object、Collection 和 Operator。
2. **意图与实现分离**：用户锁定的是“谁、何时、为何、拍成什么”，编译器选择 Blender 实现。
3. **AI 提案，不直接执行**：所有模型输出必须进入有版本的 typed schema。
4. **每次改变都有差异**：在执行前展示影响的镜头、资产、缓存、成本和预计写入。
5. **失败是一等状态**：失败不可伪装成完成，也不能因重试而消失。
6. **默认简单，完整能力可达**：普通用户看到电影工作台；专家仍能打开完整 Blender 编辑器。
7. **局部重算**：变更只使必要依赖失效。
8. **可观察与可恢复**：长任务有 manifest、心跳、阶段收据、预算和 resume 语义。
9. **质量是多目标**：结构、物理、像素、人类判断和经济性分别记录。
10. **薄分叉**：对 Blender 核心的每个改动都必须证明 Python/独立进程无法可靠实现。

## 5. 用户体验与信息架构

### 5.1 默认工作台

- 左侧：Project / Story / Scenes / Shots / Characters / Assets。
- 中央：Viewport、Storyboard、Animatic 或 Dailies，根据当前任务切换。
- 右侧：Intent Inspector，显示镜头目的、连续性约束、摄影参数、表演 beat、灯光和输出 profile。
- 底部：Job Ledger，显示计划、变更、准入、进度、预算、失败、恢复和证据。
- 顶部：Proposal、Review、Approve、Build Preview、Render Final 五个清晰阶段。

### 5.2 核心交互

用户可用自然语言提出改变，例如“保持演员和灯光不变，把 close shot 改成 85 mm，并让镜头在最后两秒慢慢靠近”。AI 不立即修改场景，而是生成：

1. 解释后的意图；
2. SceneSpec patch；
3. 影响范围；
4. 风险与缺失信息；
5. 预计成本；
6. 可预览的 BuildPlan diff。

用户批准后才执行。若构图、焦点、遮挡或资源门失败，系统显示原因和证据，并给出新提案；不会自动放宽阈值。

### 5.3 Expert Mode

Expert Mode 暴露 Blender 原生 Outliner、Dope Sheet、Graph Editor、Geometry Nodes、Shader Editor、Compositor 和 Python Console。电影层创建的稳定 ID、约束和 ownership 必须在 Expert Mode 中可识别；用户手工编辑后，系统把变化分类为受管理、显式 override 或未知漂移。

## 6. 系统架构

### 6.1 四个平面

#### A. Experience Plane

新的原生桌面 UI、电影工作台、审片、差异、时间线、成本和恢复界面。第一阶段可大量使用 Blender 现有 UI/RNA/Python；只有无法稳定表达的 editor、event 或 process control 才进入 C/C++。

#### B. Intent & Control Plane

Codex CLI、本地模型和 API 模型适配器，负责自然语言理解、方案比较、缺口提问和 SceneSpec patch。该平面不能直接持有 unrestricted `bpy` 或 shell 能力。

#### C. Deterministic Engine Plane

Schema validator、semantic validator、compiler、asset resolver、dependency graph、admission controller、Blender executor、render profiles、receipt writer 和 independent auditor。这里承接当前 BFS 代码。

#### D. Evidence Plane

内容寻址的 spec、plan、资产、场景、缓存、EXR、preview、报告、成本、失败与审片记录。该平面决定恢复和局部失效，不依赖 UI 内存状态。

### 6.2 进程边界

推荐的产品进程：

- `studio-ui`：GPL 桌面 UI，可嵌在 fork 内。
- `engine-host`：受限 Blender 进程，读取已准入 BuildPlan。
- `job-supervisor`：管理 manifest、预算、重试和进程收据。
- `model-adapter`：独立进程或远程服务，通过版本化 JSON/JSON-RPC 通信。
- `auditor`：独立实现，只读重算，不导入生产 runner。

模型服务与 GPL 引擎保持清晰边界，可以支持 Codex 订阅、本地模型和按量 API。边界的最终法律判断不能只依赖技术命名，商业发布前仍需专业许可证审查。

## 7. 核心数据模型

### 7.1 持久对象

- `ProjectSpec`：作品、帧率、色彩、交付和全局政策。
- `StorySpec`：场次、角色关系、叙事 beat 和连续性规则。
- `CharacterBible` / `ActorSpec`：身份、资产版本、比例、rig、材质、造型和允许变体。
- `SceneSpec`：一个场景的资产、关系、表演、灯光和输出意图。
- `ShotSpec`：构图、镜头、相机轨迹、焦点、时间范围、可见性和剪辑关系。
- `PerformanceSpec`：身体、面部、视线、呼吸、接触和手工 override 分层。
- `LookSpec`：灯光 rig、材质版本、曝光、OCIO 和 continuity anchors。
- `BuildPlan`：编译器生成的不可变、完全解析、顺序稳定的执行计划。
- `JobManifest`：阶段图、输入身份、预算、状态和恢复点。
- `Receipt`：一次准入、进程、阶段或产物的事实记录。
- `ReviewDecision`：机器门、人审结论、分歧和批准范围。

### 7.2 身份规则

- canonical JSON/typed binary envelope 用于合同身份；
- `.blend` 是派生产物，不是唯一语义身份；
- EXR container hash 与 decoded pixel digest 分开；
- 每个外部资产有来源、许可、版本、内容 hash 和 preferred import policy；
- 每个手工 override 有 owner、作用域和失效规则；
- 所有跨语言浮点字段声明 binary32 或 binary64 语义，禁止默认把 JSON double 当成 Blender RNA float。

## 8. AI 行动协议

AI 只被允许产生以下高层动作：

- `propose_project_structure`
- `propose_shots`
- `patch_scene_spec`
- `patch_shot_spec`
- `bind_asset`
- `set_performance_layer`
- `set_camera_intent`
- `set_look_intent`
- `request_preview`
- `request_validation`
- `request_final_render`
- `explain_failure`

每个动作必须包含 expected revision、typed payload、reason、scope、risk、estimated resources 和 approval policy。执行器拒绝未知字段、过期 revision、越权路径、未锁定资产、未声明网络、预算不足和不可解析操作。

模型永远不能以“这是 Python 代码，请执行”绕过协议。高级用户可手工编写脚本，但它属于单独、显式授权和隔离的 Expert operation。

## 9. Blender 源码介入策略

### Level 1：分发与工作区

首先完成独立应用名称、图标、启动画面、默认配置、电影工作区、菜单、快捷入口和 Expert Mode。尽可能使用现有 Python UI 与配置能力。

### Level 2：原生 Film Editor

当普通 Panel 无法稳定表达 shot graph、proposal diff、job ledger 或 evidence viewer 时，增加新的 Blender Editor/Space，并通过 RNA 暴露数据。避免把业务状态藏在全局 Python 单例。

### Level 3：稳定执行 hooks

只为已证明的缺口修改 C/C++：事务边界、无 UI 上下文操作、进程事件、结构快照、可靠取消/恢复、受控渲染回调和必要的数据访问。

### Level 4：核心算法变化

只有当产品需要 Blender 上游没有、且不能作为独立模块实现的求值或渲染能力时才进入。每项改动必须附上游合并成本、回退方案和 conformance test。

## 10. 开源、品牌与商业边界

Blender 官方代码默认 GPL-2.0-or-later；组合发布的 Blender binary 按官方说明使用 GPL-3.0-or-later。分发修改后的桌面软件时，接收者必须能够取得相应源代码，并保有 GPL 权利。调用 `bpy` 的已发布脚本也应使用 GPL 兼容许可证。内部修改而不分发时，GPL 通常不要求公开；网络服务还需根据实际组合方式和当地法律审查。

推荐边界：

- 引擎 fork、内嵌 UI、`bpy` 扩展：GPL 兼容并公开。
- SceneSpec、协议与符合性测试：倾向开放，便于生态与审计。
- 独立模型服务、托管队列和账号系统：可采用独立许可证，但必须保持真正的进程/协议边界。
- 用户作品、`.blend`、EXR 和视频：归用户，不因 Blender GPL 自动成为 GPL。
- 产品必须使用独立名称和 Logo；“基于 Blender”只能作为事实性说明。

开源不妨碍商业化。收入可以来自模型订阅、托管渲染、团队协作、资产治理、企业支持、认证发行版和服务等级，而不是依靠关闭 Blender 衍生内核。

## 11. 源码与仓库策略

不把 Blender 的多 GiB 历史直接塞进当前研究仓库。建议：

```text
film-studio/
  engine/          # Blender fork，GPL，独立仓库
  studio/          # 原生电影 UI 与工作区
  protocol/        # SceneSpec / BuildPlan / RPC
  compiler/        # 确定性编译与语义验证
  supervisor/      # Job manifest / budgets / recovery
  auditor/         # 独立只读验证
  conformance/     # 从 B01–B62 晋级的 fixtures 与 gates
  docs/            # 架构、许可证、迁移与发布说明
```

当前 `BlenderFilmStudio` 继续作为研究、协议、实验和公开证据仓库；真正的 Blender fork 在可行性 Gate F0 通过后建立独立仓库。上游策略使用官方稳定/LTS tag，维护 `upstream/blender`、最小 patch series、自动合并演练和版本迁移报告。

## 12. 发布与更新模型

- Stable channel：固定 Blender LTS、固定协议和经过审计的引擎 patch。
- Research channel：跟踪新 Blender 和实验算法，不能打开生产工程写权限。
- Project files：新版本只能通过显式 migration 打开受管理数据；保留原始备份和 migration receipt。
- Add-ons：默认禁用未知扩展；使用签名、权限声明、进程边界和资产来源清单。
- 模型适配器：通过 capability negotiation 声明结构化输出、上下文、隐私、价格和可用工具，不把供应商特性写进 SceneSpec。

## 13. 可行性 Gate F0

在宣布项目正式立项前，必须用真实源码完成：

1. **F0.1 Reproducible Build**：在当前 Apple Silicon Mac 从固定 Blender stable/LTS commit 构建可运行 binary，并保存源码、依赖和构建收据。
2. **F0.2 Independent Identity**：修改应用名称、bundle id、图标、启动画面和配置目录；不使用 Blender 商标作为产品名。
3. **F0.3 Film Workspace**：加入最小 Project / Scene / Shot / Character 工作台，同时可进入 Expert Mode。
4. **F0.4 Embedded Contract**：从 UI 接收一份冻结 SceneSpec，生成与当前外部 compiler canonical exact 的 BuildPlan，并创建 B01/B02 场景。
5. **F0.5 Render & Receipt**：无鼠标执行 EEVEE preview 和 Cycles EXR，生成进程、像素、成本和失败收据。
6. **F0.6 Upstream Merge Drill**：合并一个后续 Blender commit 区间，记录冲突文件、人工时间、测试影响和 patch surface。
7. **F0.7 Package**：制作可安装、可卸载、签名/公证路径明确的 macOS 包，验证 `.blend` 往返和配置隔离。

任何一项失败都保留原始证据，并可能改变架构。例如 F0.6 成本过高时，退回“未修改 Blender + 外部 Studio shell”；不以愿景为由继续扩大分叉。

截至 2026-08-30，F0.1–F0.7 已全部 PASS，所有失败仍保留。F0.4 attempt-03 以 manifest v0.3 把 semantic structure 与 exact product provenance 分层，在保留前两次失败的同时通过 B01/B02 隔离构建、两份 `.blend` 独立重开和四个 separation attacks。F0.5 attempt-02 不改 profile 或阈值，完成 EEVEE PNG、Cycles multilayer EXR、受控中断、receipt-only final recovery 和独立 decoded pixel/pass audit。F0.6 把 thin fork 合并到固定 Blender v5.2.1 target：0 个人工冲突路径、0 person-hours、909 行非生成 fork patch；attempt-03 保留两次 harness 失败后让冻结 F0.1–F0.5 corpus 全部保持 PASS。F0.7 attempt-05 在保留四次失败后验证341,069,106-byte unsigned DMG、read-only mount、isolated install/uninstall、官方配置隔离以及两条same-host `.blend` round trip；六个边界的core semantic hash exact，typed metadata exact preserved，independent audit 103 checks PASS。F0完成支持进入direct thin-fork产品原型，但不证明Developer ID签名、公证、Gatekeeper接受、公开发行、生产就绪或跨版本/平台通用性。

## 14. 阶段路线

### Phase A：Source Feasibility

关闭 F0，决定 direct Blender fork、Bforartists-derived fork 或外部 shell 三者中的正式基线。默认候选为 direct Blender thin fork。

### Phase B：AI-native Shell

实现电影工作台、typed action protocol、proposal diff、SceneSpec/BuildPlan、asset registry、preview、validator、job ledger 和 evidence viewer。只服务 B01/B02 与 B62 三镜头垂直切片。

### Phase C：Production Control

内嵌 B53–B59 的准入、预算、进程、磁盘、失败、恢复和审计；支持 Codex CLI、本地模型和 API provider。完成一次应用崩溃与引擎崩溃恢复演练。

### Phase D：Cinematic Vertical Slice

迁移 B62：三镜头、共享人物/环境、animatic、Cycles EXR、人工审片、成本账本和交付视频。此阶段的结束条件是一个可观看样片，而不是新增功能数量。

### Phase E：Generalization

在第二个完全不同的场景、角色和摄影风格上做留出验证；只有通过后才扩展资产生成、多人协作、插件 SDK 和跨平台发行。

## 15. 成功指标

- 从用户批准 ShotSpec 到首个可观看 preview 的时间。
- 一次通过机器准入和一次通过人审的镜头比例。
- 每个最终采用秒的人工分钟、模型用量、渲染时间、能耗和存储。
- 因变更而正确失效的依赖比例；无关镜头误重算率。
- 崩溃后不重复已完成 immutable stage 的恢复比例。
- 模型提案被批准、修改和拒绝的原因分布。
- 上游 Blender 更新的冲突文件数、修复时间和回归数。
- 没有 receipt、provenance 或 license 的产物进入 final delivery 的次数，目标为零。

## 16. 主要风险与缓解

1. **分叉债务**：薄 patch、LTS 基线、定期 merge drill、优先上游贡献。
2. **GPL 边界误判**：架构评审之外增加专业法律审查；默认公开引擎侧代码。
3. **UI 只是换皮**：以电影对象和任务状态机验收，不以隐藏按钮数量验收。
4. **AI 绕过合同**：模型无直接执行权；schema、semantic gate、capability 与 approval 强制执行。
5. **资产质量成为瓶颈**：第一阶段锁定少量人工整理资产，不假装从零生成已经解决。
6. **电影感不可量化**：机器门与人类盲评并列，保存分歧。
7. **GPU/平台差异**：定义同机 exact、跨后端 semantic、跨平台 perceptual 三层合同。
8. **磁盘和缓存失控**：JIT capacity admission、quota、内容寻址缓存、保留策略与用户可见成本预测。
9. **插件供应链**：默认关闭、签名、权限、隔离和 provenance。
10. **研究无限扩张**：每阶段以可观看垂直切片和明确停止条件结束。

## 17. 尚未解决的研究问题

- Blender 源码中实现 Film Editor 的最小 patch surface 是多少？
- Python UI 能否满足 80% 的产品需求，哪些状态必须进入 C/C++/RNA/DNA？
- 如何在不污染 `.blend` 通用兼容性的情况下持久化 ProjectSpec、ShotSpec 与 receipts？
- engine-host 和 model-adapter 的通信复杂度到何种程度仍可被视为清晰独立程序？
- Blender 上游四个月级发布节奏下，薄 fork 的真实合并成本是多少？
- macOS 签名、公证、Metal/Cycles kernel 和第三方库如何形成可重复发行？
- Expert Mode 的手工修改如何转回 typed override，而不误判用户意图？
- 如何为摄影、美术、表演和剪辑建立既可解释又不冒充导演判断的质量门？

## 18. 决策记录

### 已决定

- 长期方向是 AI 原生电影软件，而不是 UI 自动化工具。
- 直接 Blender official source 是默认基线；Bforartists 是参考实现。
- 当前 workflow 继续发展，并成为新软件的 conformance suite。
- 产品采用独立品牌，遵守 GPL，并把用户输出权利写入产品政策。
- 默认采用 hybrid architecture，模型没有 unrestricted Blender 执行权。

### F0 后仍待决定

- 最终产品名与品牌。
- Film Workspace 先用 Python UI 还是直接创建原生 Editor。
- fork 与外部 control plane 的精确仓库和发布边界。
- 第一版仅 macOS，还是同步 Windows/Linux。
- SceneSpec 持久化在 sidecar、`.blend` custom properties、Text datablock 或组合结构。

## 19. 依据与来源

1. Blender Foundation, Blender License: https://www.blender.org/about/license/
2. Blender Foundation, Trademark Policy: https://www.blender.org/about/trademark-policy/
3. Blender official source repository: https://projects.blender.org/blender/blender/src/branch/main
4. Blender Developer Documentation, Building Blender: https://developer.blender.org/docs/handbook/building_blender/
5. Blender Developer Documentation, Build Options: https://developer.blender.org/docs/handbook/building_blender/options/
6. Blender Developer Documentation, Code Layout: https://developer.blender.org/docs/features/code_layout/
7. Blender Developer Documentation, RNA: https://developer.blender.org/docs/features/core/rna/
8. Blender Developer Documentation, Release Cycle: https://developer.blender.org/docs/handbook/release_process/release_cycle/
9. Bforartists official repository: https://github.com/Bforartists/Bforartists
10. GNU Project, GPL FAQ: https://www.gnu.org/licenses/gpl-faq.html.en
11. BlenderFilmStudio research journal and B01–B62 evidence in this repository.

## 20. 下一项授权实验

`F0-SOURCE-FEASIBILITY` 的 F0.1–F0.7 已在冻结协议下全部关闭为 PASS。F0.7 attempt-05 的 verdict self hash 为 `626ea953fefd6fb1b8c3044248c653c7ce0cbc18a69a2e8eff5bb37e78a2d94a`；attempts 01–04 仍分别以 DMG timeout、pre-save depsgraph stale、两次 receipt variable-name failure 保留。协议的总体判定条件已满足，因此建议 direct Blender thin fork 进入有界产品原型。

下一项授权工作不是新增 F0.8。post-F0 repository/Phase B charter 已在 commit `6a38ca3bdd93219ec6dcd001fa72143df7d80a10` 冻结：机器合同 SHA-256 `7280a7d131d8821c7f0196e008c3c2d6961a3f713e02fc82c70028384d420098` 交叉绑定全部七个 accepted verdict、15个retained outcomes、`film-studio-engine` GPL/source/notices/upstream/release边界，以及 B01/B02 + B62 vertical slice 的 PB.1–PB.7。下一动作等待明确的repository owner、visibility、create与first-push授权；Developer ID、notarization、unsigned-DMG distribution与Phase B mutation不由该授权自动包含。

随后完成的repository-readiness实验把这个授权问题缩成两个不可混称的拓扑。当前F0 checkout是shallow，只能遍历1,165 commits，所以从它直接创建standalone remote不能满足“完整Blender历史”。只读取得GitHub `blender/blender` full mirror后，C2 attempt-03把4个fork commits接入non-shallow graph，只向本地`file://` bare repository push；destination `main` exact为`fa1b578b…`、tree `4d761fb7…`、162,917 reachable commits、merge base `9e2066ae…`，full `git fsck`通过。8/8 negative controls与独立93/93 audit通过，runner/audit self hashes为`dc1cc768…` / `b841e519…`；external repository creates、external pushes与LFS uploads全部为0。

因此建议路线已具体化为：owner `lovejzzz`、visibility `public`、从`blender/blender`创建requested name `film-studio-engine`的GitHub fork，再首次push exact F0 head为`main`。public fork路线状态为`READY_FOR_EXPLICIT_AUTHORIZATION`；private standalone mirror不是同一动作，它仍因6,671个HEAD LFS paths、全历史LFS传输、storage/bandwidth billing与owner接受而`BLOCKED`。用户明确授权前不执行fork/create/push。
