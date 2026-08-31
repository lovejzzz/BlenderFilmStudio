# PB.6 B62 three-shot vertical slice：PASS

Date: 2026-08-31

Gate: PB.6

Verdict: `PASS`

PB.6 把已审计的 B62 terminal scene package 接入 Film Studio 产品工作流。Engine source 从 `373881e1ee659a962e0015c2dac26f7fa981b1bf` 增量到 `aa4fff39ca5d5c4030dec2b8d0d4f576138787ad`，只修改三个既有 Python 产品路径，共 345 additions / 4 deletions，零 C/C++、网络、模型生成代码、shell 或 unrestricted filesystem authority。

一次 clean native arm64 build 用时 603.27 秒；随后为 receipt-backed reopen state 做一次同 build tree 的 18.70 秒增量安装，没有第二次 clean build。Accepted binary SHA-256 为 `8a380289625a2941b2a57b4905a079ffc838aed59c27f7d3ed6f49f3e7e824e6`，bundle identifier / name 保持 `studio.ainativefilm.f0` / `Film Studio Engine F0`。

正式 attempt-01 的四次产品启动分别完成：

1. 零渲染检查 exact scene、三镜头 roster、shared non-camera identity 与历史 frame-288 rejection。
2. 通过可见的 `Build B62 Review Animatic` operator 完成 WIDE / MEDIUM / CLOSE 各 96 帧，共 288 次 640×360 EEVEE render。
3. 零渲染 reopen 从 immutable receipts 重建 `288/288`、`COMPLETE`、`PASS_REVIEW_READY` typed state。
4. 零渲染拒绝 source hash、shot overlap、shared identity、删除 frame-288 rejection、把 0.90 放宽到 0.91 五项攻击，并执行独立审计。

独立审计器不导入产品 render module 或 product helper，重新解码全部 288 张 PNG。每个 shot 都有 96 个 distinct decoded frames；frame 96→97 与 192→193 两个 cut 的像素均不同。三段 camera routing、finite/dynamic pixels、三份 shot receipts、slice receipt、五份 failure receipts、640×360 / 24 fps / 288-frame H.264 review MP4 和 1920×360 contact sheet 全部通过。

关键证据：

- Evidence root: `experiments/ai-native-studio-phase-b/PB.6-2026-08-31-mac-m2max-attempt-01`
- Validation receipt self hash: `f8e1cc9d6467fd15f8c2d777584257ffa61c7f958f2b0f28c5e13c0ca826bcb1`
- Independent audit self hash: `2f7b08ee0c624cdc3580dfbcdcb2efc520280814ce4b3386e36eedd8ca3605cf`
- Slice receipt self hash: `cd9f8c4fa9b7b6fddb9086e703c070b69e7c783e34a552a04671c877d172140b`
- Review video SHA-256: `2aa51303912f920540e55638b0e21590735d73485362d75616c3dc96e22adf42`
- Review video receipt self hash: `424d4912a566aa229d01236dc7b152666635784f64dd156fb76c97fd38a3f781`
- Formal evidence: 326 files / 79,121,155 bytes；低于 512 MiB 上限。
- Product starts / renders / ffmpeg / network / model / mouse: `4 / 288 / 1 / 0 / 0 / 0`。

历史 frame-288 边界逐字保留：static correction 的 `clampedUnionAreaFraction=0.93378717684983` 大于冻结 maximum `0.90`，其 verdict 仍为 `B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT`。当前 terminal scene 使用后续 motion-aware camera；它是在没有改变 0.90 的情况下通过，不能删除或改写历史拒绝。

机器通过不等于人类审片通过。接触表显示 wide / medium / close 三种景别、核心点亮和角色面罩方向均可辨认；wide 帧含明显前景结构遮挡，medium 的核心占比较大。这些仅作为披露观察，不在 PB.6 后追加分数或改变 gate。Human review 保持 `PENDING_UNTIL_PB7`。

PB.6 的 claim 只覆盖一个继承的 stylized B62 scene、一台 admitted arm64 host 和一份 640×360 review animatic；不证明最终电影质量、photorealism、跨平台、production readiness 或 autonomous filmmaking。下一 gate 是 PB.7 human review and bounded prototype verdict。
