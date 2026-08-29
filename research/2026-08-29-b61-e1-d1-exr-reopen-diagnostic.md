# B61-E1-D1：multilayer EXR 重开接口诊断预注册

日期：2026-08-29

状态：PREREGISTERED
性质：失败后诊断，不是正式门，不产生影片质量结论

## 已证实的故障

B61 v0.2 的 C1 observability 正确捕获了首个 WIDE-A 进程的非零 Python exit。frame 1 EXR 已经 durable write，stage ledger 最后事件为 `EXR_WRITTEN`；随后 `bpy.data.images.load()` 返回的 multilayer image 在当前读取路径上具有零个 pixel values，`pixel_projection()` 因 `per_channel_count == 0` 抛出 `ZeroDivisionError`。其余五个 render process、EXR auditor 与 Node auditor均未启动。

本诊断绑定保留的 v0.2 attempt/formal tree与self-hashed failure summary。不得覆盖、修补或复用 v0.2 输出根。

## 唯一问题

Blender 5.2 自身是否提供一个可以在 background process 中、零 render call、从已落盘 multilayer EXR 唯一解析 Combined RGBA，并稳定输出 float32 little-endian projection 的原生随附接口？

候选限定为两条：

1. 复现并记录 `bpy.types.Image` 的实际 multilayer行为与相关 RNA；
2. 探测 Blender 5.2 随附 Python 环境中的 OpenImageIO，枚举 subimage/channel，唯一选择 Combined RGBA，重复解码两次并比较 exact digest。

不能安装包、不能联网、不能调用外部视频或图像模型，也不能触发 `bpy.ops.render.render`。

## 资源与接受条件

只允许一个 Blender background start、零 render call、30秒 timeout、输出不超过1 MiB。输入必须是 SHA-256 为 `a094fcae…` 的保留 EXR。接受条件是：复现 bpy pixel count 0；OpenImageIO 唯一解析 1920×1080×4 Combined RGBA；8,294,400 个float全部finite；两次float32-LE digest exact；结果和原始日志durable保留。

若任何 channel 命名或 subimage 选择存在歧义，D1直接FAIL，不允许猜测或进入formal retry。若PASS，下一步仍需另行预注册C2，才可修改正式render/auditor代码和创建fresh v0.3 roots。

## 声明边界

D1只选择可审计的磁盘EXR decoder。它不改变multilayer/half-float/ZIP格式，不改变像素exact门，不证明A/B复现，不证明电影感，也不授权正式重跑。
