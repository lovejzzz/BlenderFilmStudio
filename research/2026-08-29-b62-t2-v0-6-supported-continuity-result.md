# B62-T2 v0.6：288 帧终局 animatic 与连续性验证结果

日期：2026-08-29

状态：FORMAL MACHINE PASS / LABELED FULL-VIDEO ENGINEERING REVIEW PASS

正式 verdict：`B62_TERMINAL_288_FRAME_ANIMATIC_AND_CONTINUITY_SUPPORTED`

## 结论

T2 v0.6 在真实 Blender 5.2.0 LTS `fbe6228777e7` 上关闭了“编译后的三镜头生产场景能否在完整 288 帧时间线上正确求值、渲染、交付并独立审计”的问题。十四道冻结 gate 全部通过；独立 Blender 重新打开同一未修改 source scene，验证 288/288 路由、288/288 像素、96/96 close geometry 与冻结 causal state。随后完整 12 秒 MP4 在 QuickTime 从 00:00 无 seek 播放到时间线 00:12，并完成有标签工程连续性复核。

这项结果只支持终局 animatic 的人物、环境、镜头、光影和因果连续性，以及最终 Cycles/restart 实验的准入。它不把 640×360、16 spp Eevee、低模 Phase 0 资产称为影院级成片。

## 冻结身份

- C5 预注册提交：`6237bba64fde1519ebd101fa561bcce912d2cc62`
- 工具冻结提交：`99956b3faa5cc73af403a76c01ec38defc096706`
- source scene：`0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc`
- receipt file/self：`5fc9b1502221bba76325c60dbd2d9544a36c6f78d23bb9ac7c89dddfc91b04a2` / `4e8c0eca18f6f468f8847fc6a3b29807f29c799cead48cc4851df010d02d4fdc`
- audit file/self：`3ef56849ee2381a83fa2036788dd71500c9a418c75f4be36c850830e647016e1` / `8ae8ef95cd7b3708d8e348ab3a21ca10731b8307df9b94bdb56fdf54d3786291`
- human review file/self：`c147932f22f305a8093fe96ab5882e0f8d7114551f8e7887082337dca06c4ec3` / `760fa74bd5b915c41cf9838a2222dfc36d759e0424464430d5b93779783b3635`
- delivery MP4：360,387 bytes，SHA-256 `5203307a1c94e1b7a52cda6687d17e03143e6666ddb1f1078dd07ed6e8bbe332`
- machine root before review：300 files / 42,214,658 bytes / tree `e7d9fc6d46ff614ed5f9ce0806021973c7b6695d230b06855615f73cd5dfbc6a`
- final root with labeled review：301 files / 42,219,385 bytes / tree `9717fdca98df4af8618b94a6a288f23424eea959c8c568f3388427f23788932b`

## 实际执行

| 进程 | 结果 | 墙钟 | peak sampled RSS | 关键工作 |
| --- | --- | ---: | ---: | --- |
| BLENDER_RENDER | PASS | 41.352 s | 522,780,672 B | 288 Eevee renders；逐帧临时 EXR→OIIO→float image→PNG |
| BLENDER_INDEPENDENT | PASS | 12.863 s | 285,229,056 B | fresh reopen；288 pixels/routes；96 close frames |
| FFMPEG | PASS | 0.256 s | 134,938,624 B | 288-frame H.264 delivery |
| FFPROBE | PASS | 0.097 s | 311,296 B | 640×360 / 24 fps / 12 s / yuv420p |
| NODE_AUDIT | PASS | 0.423 s | 286,949,376 B | 14 gates 与全部 cross-bindings |

render report 记录 exact 288 render calls、288 temporary EXR writes、288 OIIO decodes、288 generated float images、0 adapter render、0 retained EXR/scratch、0 scene save、0 model/network/Docker。正式 root 仅约 42.2 MB；audit 时可用空间 303,239,876,608 bytes，高于 100 GiB reserve。

## 连续性证据

- 三个 shot 各有 96 个不同 decoded digests；全片 288/288 distinct。
- 96→97 与 192→193 两处 cut pair 均不同。
- 外部 FFmpeg 对 288 张 source PNG 做 raw RGBA framemd5，得到 288 frames / 288 unique digests。
- close frames 193–288 的 96/96 geometry rows 全部通过不变 template。
- causal checkpoints 138/143/144/150/288 exact；core activation 为 0/0/0.5/1/1，warm energy 为 0/0/2100/4200/4200。
- source `.blend` 前后 byte-exact，未保存 scene。

## 完整视频工程复核

QuickTime 打开的是 formal root 中 hash-pinned MP4，从 0 秒连续播放到 12 秒终点，没有 seek。播放内五次视觉采样覆盖三个镜头；另外打开 1/48/96/97/144/192/193/240/288 原始 PNG，并检查 24-frame delivery contact sheet。

角色外形、房间、终端位置、蓝/珊瑚光色在三镜头间一致；两个切镜有意图且可读；wide 内的靠近、medium 的 contact/core 变化、close 的 slow push 均连续。没有观察到冻结区间、资产替换或 teleport。工程 verdict 为 `FULL_VIDEO_CHARACTER_ENVIRONMENT_CAMERA_LIGHT_AND_CAUSAL_CONTINUITY_VISUALLY_SUPPORTED`。

## 限制与下一步

开场 rail/curved structure 遮挡面积很大，可能削弱最终构图；medium 长时间背向且过紧，叙事信息有限。当前画面还存在 Eevee 低采样柔化、低模资产、无音频等明确边界。

依照原始 T2 授权，下一步可以预注册最终 288 帧 Cycles EXR 渲染：必须含一次受控 Blender 中断、Codex restart、receipt-only resume、EXR 与 delivery video、成本与资源账本；在该实验通过之前不能称终局 cinematic proof 完成。
