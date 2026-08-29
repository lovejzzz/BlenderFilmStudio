# B60-E1：三镜头确定编译与共享状态一致性结果

日期：2026-08-29

正式结论：`CINEMATIC_SEQUENCE_DETERMINISTIC_COMPILE_AND_SHARED_STATE_SUPPORTED`

## 摘要

在预注册协议和工具 freeze 之后，B60-E1 使用本机真实 Blender 5.2.0 LTS，对同一 B03 人物、ActorSpec、表演、targets、灯光、world、渲染与输出契约组成的 wide / medium / close 三镜头各执行两次独立 production compile。六次编译全部通过，独立 auditor 通过 15/15 gates 与 10/10 单字段 mutation attacks。

本实验支持“结构化输入可确定编译，并在摄影机有意变化时保持人物与场景共享状态”。它不支持渲染像素复现、时间连续性、电影感、真人偏好或渲染成本结论。

## 正式输入与进程

- 预注册 commit：`97e3afee8fc44695a4a3277265a051dd1a3cf272`
- Tool-freeze commit：`0b21584c0acc653f879c2711dc76d92028bf2d70`
- Preflight evidence commit：`c6a8849`
- Blender：`5.2.0 LTS / fbe6228777e7`
- Production compiler invocations：6
- Native compile Blender starts：6
- Native child PIDs：`72780, 72799, 72813, 72827, 72841, 72855`
- Render/model/network/Docker operations：全部 0

## A/B 确定性

| Shot | Lens | PlanHash | BuildPlan file SHA-256 | Canonical structure SHA-256 | A/B exact |
|---|---:|---|---|---|---|
| WIDE | 40 mm | `518bfd62…` | `af06d37b…` | `f08f9b78…` | 是 |
| MEDIUM | 72 mm | `5213b1b3…` | `15d64a77…` | `23b5b24d…` | 是 |
| CLOSE | 100 mm | `a0689507…` | `9efd903f…` | `38cdd44a…` | 是 |

每个镜头的两份 BuildPlan 文件 SHA 完全相同；每个镜头的两份 `scene.structure.canonical.json` SHA 完全相同。

跨六次编译的共享投影只有一个 canonical hash：

- BuildPlan shared projection：`58747e63931323da2f787d0bcb6031f30c31fc0ef32d1a5e0a0baf668bbb94b7`
- Scene structure shared projection：`b158aa7023d70f106672f2a4854350adaee21acd37e666c90761f3e91247a554`
- Managed non-camera projection：`d808fef7360b0fa09befdeeb17e9cd3f52a452beba49bcb4ba28d2f06f4dbf98`

共享范围包括人物资产与 ActorSpec、rest pose、四组 mesh topology、shape-key set、144 帧表演、targets、两盏灯、world、除镜头输出目录外的 render、outputSpec、security，以及真实 Blender 场景中的 actors、asset collections、targets、render 与全部非 CAMERA managed objects。

## 负控

独立 auditor 对权威证据做十次内存深拷贝，每次只变异一个字段：人物资产 SHA、ActorSpec SHA、identityLock、rest pose SHA、mesh topology SHA、shape-key-set SHA、灯光能量、target transform、output profile、未注册摄影机参数。十次均被 semantic validator 拒绝；磁盘证据未被修改，负控 Blender 启动为 0。

## 资源与成本观测

- 六个 production compiler wrapper 总 wall time：7.293574833 s
- 六个 native budget elapsed 合计：3029 ms
- 单次 native compile elapsed 均值：504.83 ms
- 最大 sampled RSS：235,077,632 bytes
- 六次 native artifact bytes 合计：870,206 bytes
- Formal tree：58 files / 1,117,680 bytes
- Attempt tree：28 files / 57,147 bytes
- 结束后磁盘可用约 297 GiB，容量 4%

这些数据只证明场景编译阶段非常便宜；不能外推完整渲染成本。

## 发现的非确定性

同一镜头两次生成的压缩 `.blend` 文件 SHA-256 不同，而 canonical BuildPlan 与 canonical scene structure 相同。协议已明确将 `nativeBlendBytesDeterministic` 冻结为 false，因此这不是事后放宽门槛，也不影响本实验的结构性结论。

该现象说明下一阶段不能用 `.blend` 容器字节相同代替场景语义或像素相同。若未来需要内容寻址缓存，应以 canonical BuildPlan、canonical structure 和独立资产哈希为主，`.blend` 只作为绑定到 receipt 的运行产物。

## 证据摘要

- Audit file SHA/self-hash：`526625a3789eab2de78e75a316cf268332e2b6d8bc3d3d5340622bd2ef7ca7e4` / `32f65b51c9740d5fa6a33ad06bc5598f9e1eaa5f8d62c6471ecef8aa66fdc2f2`
- Results file SHA/self-hash：`2ba5dc635b4a39cd5f1e2f70522d30b319ffdc5dca8e3e062747b8de440aef32` / `36f87f767e0f70a832d6f70f376f07bae41ff6bb5a206235bb22f6b552a0e232`
- Receipt file SHA/self-hash：`12937d8519dff8a31cd7cd64477d6262ab829bb886e80efd69dbedec210e9baa` / `312060d8c0ed962642792c99f37862161ff3be969bf950394dccbb2852ccc70a`
- Attempt tree hash：`e0d35d9deb52e1a528c5c41ced6fae3fd6187c4d1ef06ea5c2b91f3062754064`
- Formal tree hash：`0e05bc6e9ff5b419f3a03672cb77b08facf099e5b287a8c3ccda1b0e8deceaa2`
- 外部只读复核：49 个 self-hashed records、六份 production receipt 与全部 receipt file identity 均重算成功；正式树中无 EXR、PNG、JPG 或 MP4。

## 对三道生产门的影响

1. 输入契约可确定编译：B60 在三镜头、六次真实进程范围内关闭。
2. 人物/场景/镜头/光影跨镜头一致：结构与契约层关闭；视觉与像素层仍未关闭。
3. 影院级渲染可复现且成本可核算：未触及。

下一项正式实验应直接复用这三份已审计 `.blend`/SceneSpec，选择少量预注册帧实际输出 EXR，分别测量像素复现、构图有效性、人物视觉一致、光影细腻度、时间连续性和单位帧/秒成本。
