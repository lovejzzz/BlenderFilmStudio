# B62-P0-E1：终局样片资产、Animatic 与 Cycles 校准准入协议

Date: 2026-08-29

Status: **preregistered before any B62 Phase 0 tool or output exists**

## 研究问题

B58 已证明编排状态可以从 durable receipts 恢复，B60 已证明三镜头可确定编译并保持共享状态，B61 已证明同机同 Blender build 的关键帧解码像素可复现并可核算成本。但当前视觉资产是技术 mannequin，不能支持终局成片。

B62-P0-E1 询问：能否在不调用生成式视频或网络服务的情况下，用真实 Blender 5.2 建立一个原创 stylized-realism 机械守夜人、轨道观测站、接触控制台与冷→暖核心状态机，生成完整 12 秒三镜头 animatic，并得到三个 1080p Cycles 关键帧与可审计资源数据，从而决定是否有资格冻结正式 288 帧协议？

本实验是终局样片的资产与 look admission，不是正式成片，也不允许用机器门宣布电影感。

## 预注册时的零状态

机器合同为 `specs/b62-phase0-asset-animatic-calibration.v0.1.json`。预注册前逐一确认六个候选工具、preflight/attempt/formal 三棵 root 均不存在；Git `HEAD` 与 `origin/main` exact，只有与本任务无关的既有用户文件保持未提交。宿主机约 296 GiB 可用，capacity sentinel 最近一次 exit 0，没有活动的 Blender render/B58/B60/B61 runner。

上游必须 exact 绑定：

- B58 C7 re-audit receipt file/self-hash：`f6112e89… / eef5dbff…`；
- B60 receipt file/self-hash：`12937d85… / 312060d8…`；
- B61 v0.5 receipt file/self-hash：`9ab3b2cf… / 18bc3a53…`。

任一文件、self-hash、status 或上游 verdict 漂移都必须在 zero-Blender preflight 阶段拒绝。

## 冻结创作合同

总时长固定为 12 秒、24 fps、frames 1–288，片名《守夜人点亮观测核心》。三个镜头各 96 帧：

1. `WIDE_APPROACH`，35 mm，frame 1–96：建立机械守夜人、观测站与冷暗核心，摄影机缓慢推进；
2. `MEDIUM_CONTACT`，65 mm，frame 97–192：右手接近并在 frame 144 与控制台 socket 接触，核心只允许在 frames 139–149 进入 cold→warm transition；
3. `CLOSE_REFLECTION`，100 mm，frame 193–288：核心保持 warm，面罩反射、眼位与反应成为视觉中心。

守夜人必须是项目原创资产，包含明确的头盔/反射面罩、发光眼缝、分层胸甲与肩甲、可动四肢、手脚及胸口状态灯。观测站必须具有圆形空间、控制台、核心、观察窗或 aperture、地面/墙面 practicals。Look 固定为冷青环境与暖金核心的 stylized realism，要求体积、景深、运动模糊、金属/玻璃反射；禁止 neural pixel replacement。

## 阶段与预算

正式 Phase 0 最多允许六个 Blender starts：

- one generator Blender，生成三份 asset libraries、one motion library、master `.blend` 与 manifests，zero render；
- one animatic Blender，以 Eevee 640×360 / 16 samples 渲染完整 288 PNG；
- three fresh calibration Blender processes，分别渲染 frames 48/144/240 的 1920×1080 Cycles CPU / 64 spp / denoise / fixed seed / multilayer half-float ZIP EXR，并从同一 scene-linear pixel source生成 review PNG；
- one independent Blender auditor，重开 master、asset libraries 与三份 EXR，zero render。

另允许 one ffmpeg process 只把 288 张 PNG 编码为 24 fps MP4，one independent Node auditor，zero model/network/Docker。总 render calls 必须为 291，其中 Eevee 288、Cycles 3。Projected writes 为 2 GiB，执行前必须满足 `100 GiB reserve + projected writes`。每个进程日志最多 16 MiB；generator/animatic/calibration/audit timeout 分别为 180/900/240/180 秒。

## 资产安全与可审计身份

每份 asset library 必须只包含合同声明的 collection、objects、meshes、materials、armature 与允许的动画数据。禁止文本脚本、Python drivers、app handlers、外部 library links、library overrides、rigid body、未声明 constraint 与运行时网络引用。生成报告必须记录：

- binary file SHA-256；
- collection/object/material/bone roster；
- canonical mesh topology、rest pose、material parameter 与 action-key digest；
- single guardian identity hash、environment identity hash、prop/state-machine hash；
- Blender version/build hash、generator version 与 process receipt。

独立 Blender auditor不得导入 generator或render脚本。它必须直接重开二进制文件，重新推导上述 rosters/digests，检查 frame 144 右手 socket 到控制台 socket距离不超过2 cm，并在 frames 138/144/150/288读取核心状态与灯光能量，证明contact先于或等于transition且warm状态不会在close shot重置。

## Animatic 与 calibration

Animatic 必须恰有288张方向正确、非空、尺寸为640×360的PNG；ffprobe必须报告24 fps、288 frames和12秒。它只用于镜头、动作、接触和状态连续性检查，不进入正式像素质量判决。

三个Cycles关键帧必须各自包含1920×1080 multilayer half-float ZIP EXR与review PNG，Combined pixels finite、nonempty、dynamic。记录每帧render/wall/CPU/peak RSS/bytes及机械的288帧投影，但不得把三张still外推称为真实全序列成本。64 spp是Phase 0 calibration dose，不预先宣布为正式B62工作点；正式samples必须在看到Phase 0证据后由新的预注册冻结。

## 判决

机器判决要求18/18 gates以及16/16 negative controls。任何false gate都映射为`B62_PHASE0_INVALIDATED`，保留当前root并停止；不得在同一ID覆盖重跑。全部通过只能得到`B62_PHASE0_ASSET_ANIMATIC_AND_CALIBRATION_ADMITTED`，表示资产/look/animatic可进入正式协议设计。

视觉检查可以记录空帧、翻转、构图、动作可读性与明显穿插，但没有匿名人类response时，`cinematicQuality`与`humanReview`必须保持false。Phase 0不授权288帧正式Cycles render，不证明写实真人或影院级成片。

## 执行顺序

1. 提交并推送本机器合同、协议与journal，保持六个工具和三棵output roots absent；
2. origin exact后实现generator/render/Blender-auditor/preflight/runner/Node-auditor；
3. 静态检查、fresh clone rehearsal与tool-freeze commit/push；
4. 主仓库zero-Blender preflight生成独立evidence commit并推送；
5. 只有runner同时绑定preregistration、tool-freeze与preflight evidence commit后，才允许创建attempt/formal roots并启动真实Blender；
6. 保留成功或失败证据，人工查看animatic/contact sheet和三个Cycles PNG，再提交结果与下一干预。
