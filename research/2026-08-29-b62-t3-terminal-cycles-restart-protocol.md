# B62-T3-E1：终局 Cycles EXR、受控中断与真实 Codex restart 协议

日期：2026-08-29

状态：PREREGISTERED — tools 与三个 formal roots 全部不存在

## 目标

T1 已证明 frozen brief → BuildPlan → production `.blend`；T2 已用完整 288 帧 Eevee、独立 Blender 与完整 MP4 复核证明人物/环境/镜头/光影/因果连续。T3 不再调整镜头或美术，只测试最后仍未成立的生产主张：同一 12 秒三镜头 scene 能否在 1920×1080、Cycles CPU、64 spp、half-float ZIP multilayer EXR 下，经一次真实 native Blender interruption 和一次真实 Codex host restart 后，从耐久 receipt 恢复、跳过已完成 wide，并完成全部 EXR、review PNG、交付视频、独立重开与成本账本。

## 为什么使用三个 shot stage

每个 96-frame shot 是一个不可变 stage。第一个 WIDE attempt 只完成 runtime/context/settings 准入，打印 ready marker 后等待 go file；supervisor 在 go file 不存在时向 exact Blender process group 发 SIGTERM，因此必须是 0 accepted render。失败 attempt 永久保留且不可晋升；`WIDE-RETRY-0002` 使用新空 root 完成 1–96。

wide PASS receipt 和 ledger event fsync 后写 Codex restart checkpoint，记录当时本机 ChatGPT/Codex `app-server` 的 PID、command 与 start identity，首 invocation exit 86。相同 host identity 再调用只能返回 `CODEX_RESTART_REQUIRED` 且启动 0 processes。用户真实重启应用后，resume 必须证明旧 identity 已死、当前 identity 不同，然后从 bytes 重建状态、验证并跳过 plan/interruption/wide，medium 才可开始。这个边界不把同一进程内的函数重入伪装成 Codex restart。

## 输出与像素桥

每个成功 shot Blender 保持 exact production Scene 为 active context，逐帧显式应用 marker/camera，exact one render call，写 16-bit half/ZIP multilayer EXR。固定 OpenImageIO 3.1.13.1 解码唯一 Combined RGBA；同一 array 形成 decoded digest，并通过临时 ACEScg Blender float image 与 isolated output Scene 写 8-bit review PNG，不增加 render call。每帧写 self-hashed report；shot receipt 绑定 96 triples、source bytes、设置与资源。

独立 fresh Blender 在 288 帧完成后重开所有 EXR，重新枚举 Combined、解码、检查 1920×1080、finite/dynamic/nonempty 与 render-report digest；它不得 render。FFmpeg 按三个成功 shot receipt 的 exact PNG roster编码 1080p H.264/yuv420p/24 fps/288 frames/12 seconds fast-start MP4，ffprobe 独立验证。

## 资源与成本

B61 在同机真实 1080p/64 spp 矩阵观察到 6.084 render seconds/frame、约 5.36 MB EXR+PNG/frame、约 4.54 GB peak RSS；Phase 0 更重的单帧观测约 35 秒。因此本协议不给出乐观 ETA：每 shot 最多 7200 秒，Blender RSS 上限 6 GiB，job 输出上限 8 GiB，projected write 6 GiB，写入后仍必须保留 100 GiB free reserve。每 stage 记录 wall/user/system、peak RSS、log/output bytes；最终报告 seconds/finished-second 与 bytes/finished-second。API 与 video-model marginal cost 冻结为 $0；不虚构 Codex subscription、硬件折旧或电费的 per-run 美元值。

## 判定边界

24/24 gates、24/24 mutation attacks、真实 Codex host identity change、288/288 Cycles renders、288 EXR/PNG/report、独立 EXR reopen、delivery 与 repeated completed resume 全部通过，才支持 `B62_TERMINAL_CYCLES_EXR_RESTART_SAFE_PROOF_SUPPORTED`。machine PASS 仍为 HUMAN_PENDING；完整 final MP4 必须再次观看并标注，之后才能发布 final boundary report。

本协议不声称低模资产变成真人级，不用像素 hash 代替审美，不包含 generative video model，不降低任何 T2 continuity gate。
