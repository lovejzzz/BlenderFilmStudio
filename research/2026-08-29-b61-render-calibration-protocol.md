# B61 前置：真实 Cycles EXR 渲染资源校准协议

日期：2026-08-29

状态：正式执行前预注册

## 目的

本校准只测量 B60 已审计场景在本机 Blender 5.2 / Cycles CPU 下渲染 1080p multilayer EXR 的实际时间、峰值常驻内存与文件规模，用于冻结 B61 正式像素复现矩阵的采样数和容量预算。它不是生产准入实验，不产生电影质量、像素确定性或跨镜头视觉一致性结论。

## 固定输入

- Source blend：`experiments/cinematic-sequence-consistency-v0-1/runs/WIDE-A/restricted/scene.blend`
- Source blend SHA-256：`9019e6dcc370dc8f9432061f144f2834497d4617afc560d2f02a2b18f1e51b29`
- Production receipt：`experiments/cinematic-sequence-consistency-v0-1/runs/WIDE-A/production-receipt.json`
- Production receipt file SHA/self-hash：`98d6ab290f425f042f62641a3b7efe826fb15a77bf49d56c70ee5ec3fc3f8232` / `9cd68189453861b98e449a8840f519cb7d857f51d4e2e8c5fdb3094bc6ef4742`
- Blender：`5.2.0 LTS / fbe6228777e7`
- Frame：72
- Engine/device：Cycles / CPU
- Resolution：1920 × 1080，100%
- Format：`OPEN_EXR_MULTILAYER`，16-bit half，ZIP lossless
- Denoise：保持已编译场景设置
- Seed：保持已编译场景固定 seed；animated seed 必须为 false

## 两个校准 case

| Case | Samples | Output |
|---|---:|---|
| CAL32 | 32 | `experiments/b61-render-calibration-v0-1/CAL32/frame-0072.exr` |
| CAL64 | 64 | `experiments/b61-render-calibration-v0-1/CAL64/frame-0072.exr` |

每个 case 启动一个独立 Blender background 进程。允许创建 exact output parent，但不得保存修改后的 `.blend`。命令必须包含 `--factory-startup` 不适用于打开现有 blend，因此使用 `--background <trusted blend> --disable-autoexec`，以 Python expression 只覆盖分辨率、samples、filepath 与帧号后调用一次 still render。

## 资源上限与失败规则

- Blender starts：2
- Render calls：2
- Frames：2
- 单进程 wall timeout：300 s
- 结束时磁盘最低 reserve：100 GiB
- Model/network/Docker：0
- 任一进程非零退出、EXR 缺失/空文件、输出越界或磁盘 reserve 失败时，校准标记 FAIL；已产生文件与日志保留，不覆盖重跑。

## 结果使用边界

若 CAL64 在资源上可接受，B61 正式矩阵优先使用 64 spp；若超过预算，允许根据本校准在正式 B61 预注册之前选择 32 spp。正式协议一旦提交，不得再根据 B61 结果修改 samples。即使两份 EXR 可读，本校准也不支持 cinema-quality claim。
