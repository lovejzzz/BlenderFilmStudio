# B62-P0-E1-C1：ffprobe 元数据探针进程记账更正

Date: 2026-08-29

Status: **preregistered during tool implementation, before tool freeze and before any B62 Phase 0 output root exists**

## 发现

父协议要求 animatic 经 `ffprobe` 报告 24 fps、288 frames 与 12 秒；父机器合同的显式进程预算却只列出 one `ffmpeg` encoding process 与 one Node auditor，没有为只读元数据探针单独记账。把探针暗藏在 Node 审计器中会使正式进程台账少报一个 child process。

## 更正

正式 Phase 0 允许且必须新增恰好 one `ffprobe` process。它只能读取已经编码的 MP4，以 JSON 输出 one video stream 的 average frame rate、decoded frame count 与 duration；不得写媒体、不得解码生成替代帧、不得访问网络。

其余冻结项完全不变：six Blender starts、291 render calls、one ffmpeg encoding process、one Node auditor、2 GiB projected writes、100 GiB reserve，以及 zero model/network/Docker。资产、镜头、像素设置、18 gates、16 attacks 与 verdict 均不改变。

更正的唯一目的，是让实际 child-process roster 与可审计预算一致，而不是放宽验收门槛。正式 preflight、runner 与 auditor 必须同时绑定父合同和本 C1 文件。
