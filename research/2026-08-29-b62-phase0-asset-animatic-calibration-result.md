# B62 Phase 0：资产—Animatic—Cycles 校准闭环结果

Date: 2026-08-29

Status: `B62_PHASE0_ASSET_ANIMATIC_AND_CALIBRATION_ADMITTED`

Runtime: Blender 5.2.0 LTS, build hash `fbe6228777e7`

Formal version: `experiments/b62-phase0-v0-4/`

## 结论

B62 Phase 0 的工程命题通过：一份冻结的结构化制作合同可以在本机真实 Blender 中生成三份独立资产库、一份动作库与 master scene，编排 12 秒 / 288 帧 / 24 fps / 三镜头时间线，渲染完整 Eevee animatic，并输出三张 1920×1080、64 spp、multilayer EXR 的 Cycles 校准帧。独立 Blender 只读重开审计与 Node audit 均通过。

这个结果不等于“电影镜头已经通过”。人工原分辨率抽查发现 `CLOSE_REFLECTION` frame 240 被前景大面积遮挡，角色与反射表意不足。该反例不修改本轮预注册 machine gate，但它会阻止我们直接支付完整 288 帧 Cycles 成本。

## 实测剂量

- Blender starts：6
- render calls：291（288 Eevee + 3 Cycles）
- ffmpeg / ffprobe / Node auditor：1 / 1 / 1
- model / network / Docker：0 / 0 / 0
- animatic：288 / 288 PNG，640×360，24 fps，12.000 s
- Cycles calibration：frames 48 / 144 / 240，1920×1080，64 spp，CPU，denoise on，fixed seed 62001
- formal gates：18 / 18
- negative-control mutations：16 / 16 rejected
- independent Blender reopen checks：23 / 23

## 成本

- process wall before Node audit：154.754865541 s
- animatic render：29.873928834 s
- three Cycles render operators：118.020115167 s
- mean Cycles still：39.340038389 s/frame
- peak process RSS：3,766,190,080 bytes
- output footprint before audit：123,021,702 bytes
- 288-frame mechanical still projection：11,329.931056 s，约 3.15 h

最后一项只是 `3 × still` 均值乘以 288，不是测得的 sequence cost；不包含模拟、跨帧缓存、完整合成、失败恢复、返工或人工审片。

## 三张校准帧

| shot | frame | decoded Combined SHA-256 | 人工观察 |
|---|---:|---|---|
| `WIDE_APPROACH` | 48 | `4db7657139dd560e0abd220322533965969e1a33ab012b3a18a858bf6b5a3238` | 环境、主体和冷光关系可读 |
| `MEDIUM_CONTACT` | 144 | `dd96de5239d48964c3d7d609625a32b4db0f27e5a4c1835e4df82082566e260b` | 接触与核心转暖可读，表演仍属 blocking |
| `CLOSE_REFLECTION` | 240 | `ca5e7a137ac320a31d28f804ad51c0f1fae658940f19cef1083cea09c382f6b9` | 前景遮挡过强，镜头质量拒绝 |

三张 EXR 的 Combined arrays 均 finite、non-empty 且有动态范围；对应 review PNG 只用于显示，不作为 scene-linear 判决面。

## 资产与一致性证据

独立 Blender auditor 在 generator 退出后重开全部文件。master 初始 external libraries 为零；三份 asset append 分别产生 54 / 84 / 16 个 tracked IDs，全部 `.library = null`。临时 source descriptor 指向精确 source `.blend`，移除 descriptor 后本地 IDs 仍存活，cleanup roster 精确。角色 required bones、materials、对象、motion action digest、相机 lens 与 transforms、右手接触、核心状态因果顺序和 cold→warm hold 全部复核通过。

## 保留的失败

1. v0.1：在 `media_type=IMAGE` 时设置 `OPEN_EXR_MULTILAYER` 失败。D1 的静态 enum 代理也被证明不可靠；D2 用三次 A→B→A 动态 setter 试验关闭该问题。
2. v0.2：`Medium High Contrast` 不存在于本机 Blender 5.2 runtime look surface。D3 还发现旧 `BLENDER_EEVEE_NEXT` 名称无效；D4 枚举并验证 neutral ACES 与 `BLENDER_EEVEE`。
3. v0.3：所有 291 renders 完成，但 auditor 在 append 后读取 library 总数，错误地把 source descriptor 当作非本地资产。D6 直接测量 ID locality；D7 以 23 / 23 corrected reopen checks 通过。
4. v0.4：使用 fresh attempt/formal roots 完整重跑，而不是追认 v0.3 已有像素。

## 复现与证据身份

- tool freeze：`20c5c4bd07d842a0131e8b14896ae72ed09734fd`
- official preflight commit：`4c76b576ca20c79cf972937e73034dfe42b40046`
- preflight self-hash：`6145aa064d0023e2f110993c95561ed47a8d8fceaa13c8c83d27ede8f1423bef`
- receipt self-hash：`462ae5409019fc1dc578dad74e9648ad1e6132641a49cffc9d73a90e770b6986`
- attempt tree：30 files / 84,420 bytes / `35a57b815889af80eb4245a0a4a0a23c4efb35f43f5073b9789fb8d32779198b`
- formal tree：311 files / 122,957,493 bytes / `3de8ee7e3f66c6507efa5befff9813f4c9473a973351a7ea4d3341a976afc321`
- animatic MP4：`7e8a2060e5d310f2fc62c9ce1150296e2e4583426a3e541cad2ea45934efbfb7`

与 retained v0.3 的描述性复现比较显示：三张 Cycles 的 decoded Combined pixel digests、三张 calibration PNG、资产 identity、motion action 与 final MP4 均 exact；288 张 individual animatic PNG container hashes 为 0 / 288 exact，推测来自非语义 metadata/container 差异。没有额外 decoded-pixel 试验，因此不主张 288 帧像素 exact。

## Claim boundary

本轮支持：

- 结构化意图到真实 Blender 资产、动作、三镜头 master 与 animatic 的闭环；
- 可重开审计的资产 locality、身份、camera、contact 与 lighting state；
- 三张高质量格式的 Cycles 校准输出与本机成本测量；
- 不依赖生成式视频模型的生产控制路径。

本轮不支持：

- 完整 288 帧 Cycles sequence 已渲染或已复现；
- camera composition、blocking 或节奏达到电影级；
- photoreal human、皮肤、毛发、服装、表情与微表演；
- 人类盲评或最终审片通过；
- 跨机器、跨 GPU 或跨 Blender build 的像素复现。

## 下一门

先预注册并运行 `B62-CAMERA-QUALITY`：在三个关键帧与低成本 animatic 上测量主体可见面积、前景遮挡、视觉中心、焦点、曝光/高光、镜头运动与剪辑可读性；明确拒绝 CLOSE 当前构图。只有 camera-quality gate 通过，才有资格运行完整 288 帧 Cycles 与 restart-safe terminal delivery。
