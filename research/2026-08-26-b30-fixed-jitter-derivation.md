# B30 derivation · fixed filter-jitter candidate selection

日期：2026-08-26（America/New_York）  
状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`

## 问题与边界

B29 发现 PNG/Combined 的双模式，以及不总与它耦合的 CryptoObject00 coverage 模式。Blender 5.2 release 源码中的 `Sampling::init` 读取隐藏 scene custom property `override_pixel_jitter_sample`，允许把 filter jitter 固定为一个二维位置。B30 derivation 只问：哪个预先列出的固定位置值得进入下一次自然抖动对固定抖动的确认实验？

这不是机制确认，也不是生产修复。固定一个 filter-jitter 点会改变采样目标，可能牺牲抗锯齿和亚像素积分质量。

## 探索设计

四个 cell 各启动一个全新的真实 Blender 5.2.0 LTS 进程，在 frame 38 连续 render 12 次：

- `NATURAL`：不写 custom property；
- `CENTER`：`[0, 0]`；
- `POS_QUARTER`：`[0.25, 0.25]`；
- `NEG_QUARTER`：`[-0.25, -0.25]`。

共 4 个 PID、48 次 render。所有 cell 使用同一源 `.blend`、同一 configurator、Eevee 32 samples、dither 0、Fast GI on、TAA reprojection on、FIXED/8 threads。输出只用于派生候选，不设置确认性支持阈值。

候选选择规则是在分析前写入 analyzer 的：只要 `CENTER` 在 cell 内 decoded RGB exact，就提名 `CENTER`；与自然输出的图像差异必须完整保留为干预代价，不能事后优化一个“更接近”的阈值。

## 观察

`NATURAL` 在一个 PID 的 12 次调用中复现两个冻结模式：REFERENCE 7 次、ALTERNATE 5 次。三个固定 jitter cell 各自都是 12/12 decoded RGB exact，但三者得到三个互不相同的新 hash：

- `CENTER`：`ba0591ae…ff8aca`；
- `POS_QUARTER`：`2c9dc178…b3bd54`；
- `NEG_QUARTER`：`90cedab5…9b84a5`。

因此探索规则提名 `CENTER` 进入确认实验，但不能把 12/12 单 PID exact 外推为跨进程稳定。

固定位置不是对自然图像的无损锁定。相对冻结 REFERENCE：

- `CENTER` 改变 131,779 / 518,400 个像素，212,525 个 channel values，最大 46 code values，normalized RMS `0.0036968892`；
- `POS_QUARTER` 改变 131,482 个像素，最大 41 code values；
- `NEG_QUARTER` 改变 128,180 个像素，最大 51 code values。

三组差异 bbox 都覆盖全幅 `x=0–959, y=0–539`。三个固定 cell 彼此也改变约 127,701–143,424 个像素。这说明干预锁定的是另一个采样结果，不是把 B28 的 17-pixel 双模式简单钉在 REFERENCE 上。

## 能说与不能说

可以说：在这次探索的单个 PID 中，固定三种 jitter 值都消除了 cell 内的 decoded RGB 切换；自然对照同时复现了双模式，因此 `CENTER` 是一个有信息量的正式干预候选。

不能说：固定 jitter 已被证明跨进程稳定、已识别根因、改善电影感、改善抗锯齿，或适合作为默认生产配置。全幅变化是明确的干预成本；它的感知质量必须由独立图像/视频质量协议另行评估。

## 冻结身份

- Blender binary SHA：`60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`；
- scene `.blend` SHA：`2a5053601cbd98d7b404069454ff7b2b710aa885541c4972b5d3f6c216511b0b`；
- OCIO SHA：`24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15`；
- derivation result SHA：`3c0f45dbd1c84b16f7876e5060275c6992aa86006bef12742075f16ced18a3f6`；
- analysis SHA：`b8d32410392b9c717777d840b61313484d50aff4114c6248fefd1b82a4b06b0e`。

下一步必须在看见任何正式输出前冻结 `NATURAL` 与 `CENTER` 的跨 PID 样本数、hash identity、novel-mode 处理、自然对照复现门槛和固定 cell 失败优先级。

Artifacts: `experiments/fixed-jitter-derivation-v0-1/results.json`, `experiments/fixed-jitter-derivation-v0-1/analysis.json`, `experiments/fixed-jitter-derivation-v0-1/evidence/`, `blender/explore_b30_fixed_jitter.py` and `blender/analyze_b30_fixed_jitter_derivation.py`.
