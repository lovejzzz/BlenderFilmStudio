# B52-D8 · External canonical warp → Blender Raw EXR bridge 结果

日期：2026-08-27

## 结论

`EXTERNAL_CANONICAL_WARP_BRIDGE_SUPPORTED`

在冻结的 Blender 5.2.0 LTS、CPU compositor、单线程、Raw input 与 `Image → Group Output` 一-link 边界中，外部 canonical float32 warp 可以通过 FLOAT/ZIP EXR 进入 Blender，再以 RGBA32/ZIP EXR 输出，decoded canonical RGBA float32 完全不变。

这是一个精确的工程结论，不是主观画质判断。它支持把高频/边界敏感的 warp 算法留在 Blender 外部，同时让 Blender 继续负责几何、材质、灯光、相机、分层渲染与后续已验证边界。

## 正式矩阵

- 3 个未见 fixture：signed HDR + Clip、high-frequency HDR + Extend、unique-edge + destination-varying Repeat；
- 3 个 Python producer 进程 + 3 个独立 Node producer 进程；
- 6 个 OpenImageIO EXR encoder 进程；
- 12 个全新 Blender 5.2 后台进程，每个 producer-fixture 两次；
- 共 24 个唯一 PID、12 次 compositor render、0 次 Cycles ray render、0 个 source `.blend`；
- 12 次生成 EXR asset open。

## 测量结果

三个 fixture 均同时满足：

- Python 与 Node canonical `.rgba32` byte exact；
- 两条 producer 路径的 EXR encode→decode exact；
- 四份 Blender output（2 producer × 2 repeat）相对 canonical raw exact；
- Blender repeat exact，producer path convergence exact；
- maximum absolute error = 0；
- changed scalar count = 0；
- finite、negative RGB、RGB>1、non-opaque alpha 与 orientation corner sentinel 全部保留。

24/24 adversarial attacks 通过。结果 self-hash、evidence core、全部报告/PID/roster、runtime、parent、graph/RNA、EXR layout、output hash 与 diagnostics 均绑定。

## 独立审计

Audit 状态 `PASS`：

- 6/6 producer replay exact；
- 6/6 encoder decoded replay exact；
- 24/24 formal run artifacts exact；
- analyzer replay byte exact；
- 12/12 diagnostic artifacts 与 replay byte exact；
- operation counts 与 scientific verdict 一致。

关键文件 SHA-256：

- `run.receipt.json`: `b6676f6320165374fe4bcd145c26edb53aca0a93a4b4bda20a81075c018d22c3`
- `results.json`: `153340e4f7d76bb9e530a26347e6582974850d7fdcb423b1b7799aaa7ad3a1fb`
- `audit.json`: `8ded86e46e0fdb6b99b55c304317d09ea6db4b4c8b9bbd553bd578ea93bee8fd`
- audit self-hash: `c28be43b8cdeaaaad2a1eb4c2d7c7f362aadff6bc8b6512f16270b28bdcb68d6`

## 边界与下一步

D8 不恢复 D7 对 Blender Bilinear consumer 的负结论，也不证明任意 compositor node 都无损。它只验证冻结的一-link pass-through。

下一步是 B52-D9：预注册 layer/depth-aware external temporal accumulation。D9 必须显式定义 layer ownership、depth/occlusion rejection、motion-vector convention、history validity、disocclusion fill 和 deterministic accumulation；D8 只作为输入/输出 transport，不作为 temporal correctness 证据。

D8 不证明 depth、occlusion、temporal stability、motion blur、denoising、Cycles production render、电影感或人类偏好。
