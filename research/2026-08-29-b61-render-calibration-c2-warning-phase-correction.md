# B61 校准 C2：区分 startup-scene 迁移警告与目标 `.blend` 颜色漂移

日期：2026-08-29

状态：v0.3 执行前预注册

## v0.2 反例

v0.2 在 Blender 启动前正确设置了冻结的 `OCIO`，CAL32 的四项 target-scene in-process assertions 全部通过并写出 EXR；但 stdout 有五条 `color_management | WARNING`，违反 C1 冻结的 zero-warning gate，因此 CAL32 不可准入，CAL64 按 fail-closed 顺序没有启动。

五条 warning 全部发生在日志中的目标 `blend | Read blend:` 之前。内容是 Blender 默认 startup scene 的 built-in `sRGB / AgX / Standard` 设置在进程载入自定义 ACES config 时迁移到 `sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709) / Un-tone-mapped`。它们不是目标 `.blend` 从冻结配置回退；但 v0.2 事前阈值没有区分时间阶段，所以仍必须失败。

v0.2 failure file SHA/self-hash为 `b3cb19fd51117dd91ddc3c0b72bb1ec69c0e180eb8f4b6db180b42fb0624fd85 / efe31eda9b2cf5f7e0ad757158c3f734ff2f416aace2dd3733acecebef896889`。整个 root 固定为 4 files / 1,382,142 bytes / tree hash `f3c2d8bc0b54f671c8c9bf3edb16cdbb9713af776e19a700fde2e323177acd8e`，不得覆盖或复用。

## 唯一授权修正

v0.3 使用 fresh root `experiments/b61-render-calibration-v0-3`。输入、OCIO environment、frame、resolution、samples、engine/device、format、timeout、资源上限与四项 in-process assertions 全部保持 v0.2 exact。

只把日志门从“全 stdout 零 color warning”修正为阶段化规则：

1. 必须出现 exact `Using OCIO=<frozen path>`；
2. 必须出现目标 `blend | Read blend: "<frozen source blend>"`；
3. 允许发生在目标 `Read blend` 之前的 startup-scene migration warning；
4. 目标 `Read blend` 之后任何 `color_management | WARNING` 都拒绝；
5. 进程内 config SHA/name、display、view 四项仍必须 exact；
6. 保存 EXR 的日志必须发生在目标 `Read blend` 之后。

不允许简单删除所有 warning 或只检查进程 exit 0。阶段顺序、目标路径与 in-process state 必须同时满足。

## 结论边界

v0.3 若通过，只说明 CAL32/CAL64 的资源观测来自正确加载冻结 ACES config 的目标场景。它不改变“校准非正式准入”的边界，也不支持像素确定性或电影质量。
