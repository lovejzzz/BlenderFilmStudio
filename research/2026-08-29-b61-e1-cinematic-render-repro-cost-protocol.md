# B61-E1：三镜头 Cycles EXR 像素复现与成本协议 v0.1

日期：2026-08-29

状态：正式实验前预注册

## 研究问题

B60 已证明三镜头的结构化输入、人物/场景/光影共享状态可确定编译，但没有产生像素。B61-E1 检验同一宿主机、同一 Blender 5.2 build、同一 CPU、固定 seed 与冻结 ACES 配置下，三个镜头的关键帧能否在独立进程中重现相同的解码后 Combined 像素，并给出可审计的实际资源与成本数据。

## 固定矩阵

机器可读协议为 `specs/cinematic-render-repro-cost.v0.1.json`。输入绑定 B60 的 WIDE-A、MEDIUM-A、CLOSE-A 三份已审计 `.blend`。每个镜头渲染 frame 1、72、144；A/B 两次重复必须由不同 Blender background 进程完成。总计 6 个 render Blender starts、18 次 `bpy.ops.render.render`、18 个 EXR、18 个 PNG 与 18 个 pixel report。

所有 case 固定为 1920×1080、Cycles CPU、64 spp、denoise on、seed 24082960、animated seed false、multilayer half-float ZIP EXR。64 spp、120 s timeout 与 100 GiB reserve 来自已推送的 v0.3 真实校准，不允许在看到 B61 结果后修改。

## 颜色管线

每个 Blender 进程启动前必须注入冻结 OCIO 绝对路径并重算配置 SHA。允许 Blender 在读取目标 `.blend` 前迁移 default startup scene；目标 `Read blend` 之后任何 color-management warning 都拒绝。Render 前再次断言 scene 内记录的 OCIO SHA/name、display 与 view exact。

## 像素复现定义

EXR 容器字节不是像素复现的判据。每帧写出 EXR 后，render process 必须用 Blender 5.2 重新打开该 EXR，从解码后的 Combined RGBA 取得 1920×1080×4 个 float32 值，以 little-endian byte order 计算 SHA-256，并记录 finite count、non-finite count、各通道 min/max/mean 与 dynamic range。

独立 artifact-audit Blender process 在所有 render processes 结束后再次打开 18 个 EXR并重算同一 projection。每个 shot/frame 的 A/B digest 必须 exact；artifact audit digest 必须与对应 render report exact。不得用 EXR file hash、PNG hash或视觉近似替代 decoded pixel digest。任何一个 pair 不同即正式失败，不引入事后容差。

## Review proxy

每次 render 完成后可从同一 Render Result 保存一份 8-bit PNG，不允许再次调用 render。PNG 用于本轮之后的构图/人物/光影研究与真人评审，不参与技术复现 verdict。若画面明显无人物、全黑或构图无效，必须在结果中报告；即使像素完全复现，也不能据此宣布电影质量通过。

## 成本记录

Runner 必须记录每进程 wall time、每帧 render time、user/system time、maximum resident set size、EXR/PNG/report bytes、总字节和磁盘前后值。结果可计算本机同场景的平均秒/帧，以及按24 fps线性外推的每成片秒和每成片分钟时间；这些外推必须明确标记为非完整序列实测，不能包含人工、资产制作、失败重试或跨硬件成本。

## 十个负控

独立 auditor 必须拒绝：source blend hash、production receipt hash、OCIO 缺失、目标 blend 后 color warning、samples、resolution、animated seed、pixel digest、frame roster，以及把 container hash冒充pixel digest的单字段变异。负控只作用于内存深拷贝，不修改正式证据，不启动额外 Blender。

## 预注册时不存在的工具与输出

以下 candidate tools 在本协议提交时必须不存在：

- `blender/render_b61_frames.py`
- `blender/audit_b61_exr.py`
- `scripts/preflight-b61-e1-cinematic-render-repro-cost.mjs`
- `scripts/run-b61-e1-cinematic-render-repro-cost.mjs`
- `scripts/audit-b61-e1-cinematic-render-repro-cost.mjs`

以下 roots 必须不存在：

- `experiments/cinematic-render-repro-cost-preflight-v0-1`
- `experiments/cinematic-render-repro-cost-attempt-v0-1`
- `experiments/cinematic-render-repro-cost-v0-1`

## 结论边界

B61 即使通过，也只支持同机同build、九个代表性shot/frame pair的技术像素复现与成本核算。它不支持`.blend`或EXR容器字节确定、跨硬件复现、全144帧时间连续、真人视觉身份、电影感、影院显示校准或完整成片成本。后续必须用PNG/EXR review进入视觉与电影质量门，不能把技术确定性冒充审美质量。
