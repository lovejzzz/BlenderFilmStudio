# B61-E1：三镜头 Cycles EXR 像素复现与成本结果

Date: 2026-08-29

Status: **PASS — technical reproducibility and cost supported**

Formal receipt: `18bc3a53e45e353d87304e165e821d5b94c9e30c510da6c76b943a83f6fe3244`

## 研究问题

B60 已证明 WIDE、MEDIUM、CLOSE 三个镜头可以从冻结输入确定编译，但没有产生像素。B61-E1 检验：在同一宿主机、同一 Blender 5.2 build、同一 CPU、固定 seed 与冻结 ACES 配置下，三个镜头的关键帧能否在相互独立的 A/B Blender 进程中重现相同的解码后 Combined 像素，并留下实际时间、内存和文件成本。

协议在正式输出 root 出现前冻结并推送。矩阵固定为 3 个镜头 × frames 1/72/144 × A/B，共 6 个真实 render Blender starts、18 个 render calls、18 份 multilayer EXR、18 份 review PNG、18 份 self-hashed pixel report；另由第 7 个 Blender 进程独立重开全部 EXR。渲染参数为 1920×1080、Cycles CPU、64 spp、denoise on、seed `24082960`、animated seed false、half-float ZIP multilayer EXR、冻结 OCIO，单进程 timeout 120 秒并保留 100 GiB 磁盘余量。

## 正式结果

- 16/16 frozen gates 通过；10/10 negative-control mutations 被拒绝。
- 6/6 render Blender processes exit 0，并留下 terminal `BFS_B61_RENDER_OK`；18/18 render calls 完成。
- 18/18 EXR、PNG、pixel-report triples 完整；所有 pixel reports finite、nonempty、dynamic，self-hash 有效。
- 9/9 A/B shot-frame pairs 的解码后 Combined RGBA float32-LE digest exact。
- 9/9 PNG container SHA exact；9/9 EXR container SHA 不相等。正式 identity surface 是解码后的 Combined 像素，不是 EXR 容器字节。
- 独立 Blender EXR auditor 重开 18 个 EXR，重新枚举唯一 Combined RGBA quartet，并与 render-side reports exact 匹配。
- 所有进程使用冻结 OCIO，目标 `.blend` 读取后的 color warning 为 0；未留下运行中的 Blender 进程。
- operations：7 Blender starts（其中 6 render、1 zero-render audit）、18 renders、0 model、0 network、0 Docker。

三组代表性像素 digest：

| Shot | Frame 1 | Frame 72 | Frame 144 |
| --- | --- | --- | --- |
| WIDE | `192237bde2f6…` | `514aac2ab1c3…` | `b842bb5ce630…` |
| MEDIUM | `9d6ca4303b22…` | `577413dddfc9…` | `d364595bbfe9…` |
| CLOSE | `bb213fb84a74…` | `f69a02d03416…` | `4809d28b335b…` |

## 实测成本

18 帧 render operator 总计 `109.506 s`，均值 `6.084 s/frame`；6 个进程 wall time 合计 `121.366 s`。在只按当前九个 still-frame 样本机械外推、24 fps、忽略启动摊销变化和时间连续性成本时，得到约 `146.008 s wall / finished second`，或 `8,760.494 s ≈ 2.433 h wall / finished minute`。

文件总量为 `96,531,022 bytes`；其中 18 个 EXR 合计 `91,620,900 bytes`，18 个 PNG 合计 `4,864,796 bytes`，每个 rendered frame 的 EXR+PNG 平均约 `5.36 MB`。六个 render processes 的最大常驻内存在约 `4.50–4.54 GB`。这些是本机真实观察值，不是云端报价，也不是完整镜头成本。

## 被保留的失败路径

正式 PASS 不是第一次尝试得到的：

1. v0.1 在首份 EXR 后暴露 Python exit code 与原始日志缺口；C1 增加可观察性。
2. v0.2 证明 `bpy.data.images.load(multilayer).pixels` 在该路径为空；D1–D3 验证 Blender bundled OpenImageIO decoder，并修正 Python/Node integral-float canonicalization。
3. v0.3 证明 active production scene 的 image format 被 `OPEN_EXR_MULTILAYER` 枚举锁定；D4 验证 isolated review scene。
4. v0.4 证明 headless `Render Result` 没有 image data；D5 验证从同一次 OIIO RGBA array 创建 Blender float image，C4 据此生成 review PNG。

上述失败 root、raw logs、stage ledgers、诊断 result/receipt 和修正预注册全部保留。v0.5 没有放宽原 16 个门、10 个攻击、渲染参数或成本边界。

## 人工可视检查

九张 A-run review PNG 组成 3×3 接触表后按原分辨率检查：图像方向正确，颜色与照明可读，WIDE → MEDIUM → CLOSE 的景别变化清楚，frames 1/72/144 的运动与眼位发生变化；未见空帧、翻转或明显数据损坏。

几何体是刻意简化的低多边形测试资产。该检查**不支持**电影级美术、真人皮肤、头发、服装、微表演或角色身份判断。

## 声明边界

本实验只支持：

> 在同一宿主机、同一 Blender 5.2 build、冻结 CPU/Cycles/OCIO/seed 条件下，九个已抽样 shot-frame pair 的解码后 Combined 像素可以独立复现；对应资源与机械成本可以审计。

本实验不支持：跨硬件复现、EXR 容器字节确定性、全 144 帧时间连续性、完整序列渲染成本、真人视觉身份、电影感、影院显示校准或完成成片。

下一道门必须直接使用真实英雄角色、受控材质与灯光、至少三个连续镜头和匿名人类审片，分别测量身份、造型、光影、运动与摄影连续性；不能继续用像素哈希替代审美判断。

## 可审计证据

- Formal audit file SHA-256: `7bef5611b7c1c14cb8a6c67c320a28b33e5c30cb12964c616cdccfd4bd39fe67`; self-hash: `ad8b6c10296178bcef912b74b10a08aba93e7cd0dac061157f420bc76592fe3f`
- Results file SHA-256: `1477cc0088d56a33b3f04388742f2321ae85d2e1e4de1f1cb12aa029953344b2`; self-hash: `b3730720fcae2f09700575472b34ca1bf8bf6101367123738fdbd2a36fbed747`
- Receipt file SHA-256: `9ab3b2cfb1aef3829abff6292aab285226a6b51cf9f376b60214de85626766de`; self-hash: `18bc3a53e45e353d87304e165e821d5b94c9e30c510da6c76b943a83f6fe3244`
- EXR reopen audit file SHA-256: `9af1fb4beeedd6281c013343bc82cf3c5a5ad38e4fa047cfb09b607b3bb7021a`; self-hash: `95535d555e4c1304e9191506a68d151b7c2eec5fb73eabd7c7016753888b6fe7`
- Attempt tree: 27 files / 30,131 bytes / `4ee442ffa07e181cf27410d784658fb049e21e7dfe7c03021ee586c867ce89cc`
- Formal tree: 71 files / 96,621,748 bytes / `21ddfcfb02783080cb77cb7431c96924d8efaa1dc2d7e92a558a84b83104518b`
