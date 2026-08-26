# B35 protocol · delayed-disclosure independent human review

日期：2026-08-26（America/New_York）

状态：`PREREGISTERED_BEFORE_B35_TOOLING_OUTPUTS_OR_RESPONSES`

机器可读实验契约：`specs/human-quadrature-review-spec.v0.2.json`；SHA-256：`2a6af8e5d084b29dd51fc69acb3a96223cae477c85c815ea48c2667781ebf83f`。

若设计、输出披露顺序或人类判定门槛改变，只能建立新版本；不得静默改写 v0.2 spec。B35 的目标不是“终于做出支持 Q8 的结果”，而是给 Q8、NATURAL、无方向差异和观察者分歧提供对称的胜出与失败条件。

## 先记录 B34 为什么失败

B34 的渲染、scene-linear 合成、lossless carrier、响应验证器和界面工程均通过；但公开 `package.manifest.json` 暴露了 `method → carrier SHA`，observer HTML 暴露了 `CLIP → 同一 carrier SHA`。不读取 sealed mapping、salt 或 analyzer，只按 SHA join，就能在 18/18 session 恢复三个方法。

因此 B34 是一个有用的工程结果，也是一个正式盲法反例。其 human count 保持 0/18，禁止继续采集。B35 不复用任何 B34 图像、carrier、decoded frame、mapping 或 session。

## 可证伪问题

在记录但不统一的 remote viewing 条件下，18 名未直接参与开发的独立观察者，是否对一个全新六秒 realization 的 STRATIFIED8 与 NATURAL32 给出方向一致的 temporal-stability preference？QUADRATURE4 只作诊断点，不得改变主结论。

主假设支持门槛保持 B34 原值：18 人中至少 14 人方向性选择 Q8，且把 Q8 评为 MILD-or-worse 的人数不高于 NATURAL。NATURAL 使用完全对称门槛；至少 14 人选 indistinguishable 且两主方法各自 MILD-or-worse 不超过 2 人，才允许无方向差异结论；其他情况为 `OBSERVER_DISAGREEMENT`。

1–14 名有效观察者只能是 `INFORMAL_REVIEW_ONLY`；15–17 名是 `FORMAL_REVIEW_INCOMPLETE`。任何 collection-close 前的 method-to-CLIP 可关联泄露，使整项研究成为 `BLINDING_BREACH_INVALID_STUDY`，而不是事后剔除几个可疑参与者。

## 新视觉 realization

源 `.blend`、plan 与 structure 保持字节绑定。每个 fresh Blender process 打开源场景后必须先观察 active camera lens 为 `50.0 mm`，再只在内存中统一设为 `52.0 mm`；不保存源文件，不改变 camera transform、timeline 或方法之间的其他条件。

固定 frame 1–144、24 fps、960×540、motion blur off：

- NATURAL32：1 个新 PID、144 renders；
- Q4：4 个固定 jitter component PID、576 renders；
- Q8：8 个固定 jitter component PID、1,152 renders；
- 合计 13 个唯一 PID、1,872 个新 float32 EXR。

Q4/Q8 仍只在 scene-linear RGB 等权合成。统一通过冻结的 Blender/OCIO ACES 2 display transform 输出 PNG8，再编码成 lossless VP9 Profile 1 `gbrp` WebM；144/144 decoded RGB 必须与 display PNG pixel exact。

B35 每个方法的 display sequence 与 carrier 必须不同于 B34 对应方法。任何相等都意味着“新 realization”失败并阻止采集。52 mm 干预是方法对称的控制变量，不是对画质提升的预测。

## Delayed disclosure 是实验变量

正式采集关闭前，以下内容只能存在于 ignored private work：

- B35 所有 method-labelled source/output/carrier/decoded/display hashes 与 manifests；
- mappings、salts、unblinding keys；
- observer 的 CLIP-to-carrier hashes、session packages；
- collection-open 期间的 accepted responses 与 ledger。

采集前允许公开的只有：本 protocol/spec、不含输出身份的工具源码与工具哈希、一个对完整私有 package manifest 的 salted commitment、以及不列出敏感值的 leak-audit 计数和 registry commitment。

私有 sensitive-hash registry 必须覆盖每个 B35 output、carrier、decoded frame、display frame 与 mapping identity。正式采集打开前以及每一次 response 被接受前，扫描完整 git-tracked tree 与 public site build；除不具可连接性的 salted commitment 外，registry 中任何值出现次数必须为零。

每个 observer package 还必须扫描 method labels、其他 session 身份、source path、公开仓库链接与解盲材料。可见的 `CLIP-01/02/03` carrier hashes 可以绑定该观察者 response，但在 collection close 前不得进入公开仓库，也不得与方法建立公开关联。

只有两种关闭方式：

1. 18 份有效且六种顺序各三份的 response 全部 hash-lock；或
2. 冻结 `ABORTED_NO_FORMAL_RESULT`，此后该版本永不恢复采集。

关闭记录必须先于 mapping、salt、method-labelled hashes 和 analyzer disclosure。若提前泄露，结论是失盲无效，不允许“修页面后继续”。

## 观察者与界面

- 目标 18 名独立、未直接参与系统开发的观察者；owner/developer pilot 不计数。
- 三个 clip 各完整播放两次，1×；primary interface 无 pause、seek、loop 或速率控制。
- 正式显示器至少 1920×1080，browser zoom 100%，视频 CSS 960×540。
- 刷新率必须是 24 的整数倍，只接受 48/72/96/120/144/240 Hz。
- 每次播放记录 total/dropped video frames；任何 dropped frame 使该 session 无效。
- 记录匿名 ID、经验类别、视觉筛查类别、显示器/刷新率、browser/OS、距离、亮度和环境；不收集姓名、邮箱或原始健康资料。

这是 participant-blind 设计。工具不得向操作日志打印 mapping 或敏感 hashes；但当前没有独立第三方 key escrow，因此不声明 operator double-blind。这个限制必须与结果一起报告。

## 资源、失败保留与清理

正式渲染前磁盘可用空间至少 8 GiB，B35 work 必须为空。B34 ignored raw work 只有在其 committed evidence、公开失盲反例和精确删除范围已记录后才可清理；它仍可由冻结 commit/spec/tool 重建。

B35 private raw work 至少保留到 collection close 与 delayed disclosure evidence 提交。首轮失败、报告期异常、反例攻击、环境身份、PID、random/jitter controls 与原始 hashes 都必须保留；不能只保存最后一次成功摘要。

## 攻击优先

package ready 之前至少攻击：旧 B34 视觉复用、lens 干预缺失、runtime/spec/scene 置换、render schedule 改动、PID/EXR 缺失或重复、空间不足、合成/显示变换改变、carrier metadata 与 roundtrip、公开 tracked-tree registry 泄露、public hash join、observer package 方法词泄露、public tree 变化后未重审、未执行 same-state leak audit 即接收 response、提前 unblind、developer/synthetic/duplicate 计数、response mutation/binding/viewing telemetry，以及低于 18 人运行正式决策。

攻击工具本身必须在生成被测 B35 outputs 前冻结；独立审计需从 factory-startup/净进程重新计算关键证据。攻击失败必须作为结果，不得被随后修复覆盖。

## 证据分层

- **Measured fact**：真实 Blender PID、文件数、hash、像素 exactness、播放 telemetry、response ledger 与 leak scan。
- **Inference**：只有在冻结门槛通过后，关于“该 realization、这些观察者与记录条件”的 temporal-stability 结论。
- **Subjective judgment**：只能来自满足独立性和 viewing validity 的真人 response。
- **Unknown**：operator expectancy 的实际影响、未统一显示器影响、跨场景/机器外推、motion blur、4K 投影、表演、叙事、photorealism 与整体电影感。

synthetic fixture 只能证明 validator/analyzer 会拒绝或分类某种输入；developer pilot 只能证明界面路径。两者都不是第 1 位观察者。

## 标准边界

截至本次预注册，ITU 官方目录将 [ITU-R BT.500-15](https://www.itu.int/rec/R-REC-BT.500-15-202305-I/en) 标为 in force (Main)。B35 受其观察记录思想启发，但没有校准实验室、统一显示器与独立 operator escrow，所以不能写成 “BT.500 compliant laboratory test”。

## 非声明

即使正式门槛通过，也不证明 Q8 普遍优于 NATURAL、不证明最优采样点、不证明跨镜头/跨机器稳定、不证明 motion blur 或交付编码质量，更不证明人物一致性、表演、photorealism 或电影感。它只回答冻结的 temporal-stability 人类判断问题。

## Freeze statement

本提交前，B35 renderer/configurator、private package manifest、sensitive-hash registry、leak auditor、new EXR/PNG/WebM、mapping/session、response validator、collection ledger 与 delayed-disclosure analyzer 均不存在。下一提交才能创建工具；再下一阶段才能产生被测输出。
