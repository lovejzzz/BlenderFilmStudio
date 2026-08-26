# B29 derivation · frame 38 pass-domain exploratory pilot

日期：2026-08-26（America/New_York）  
状态：`EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`

## 为什么先做 pilot

B28 已确认两个 decoded RGB mode 会在同一 PID 的相邻 render invocation 之间切换，但不能区分几何/可见性、radiance accumulation、film resampling、GPU execution 或 output readback。正式 B29 的 pass 和门槛不能在看见正式输出后再选择，因此先用一个明确不晋级的单进程 pilot 选择观测域。

Blender 5.2 release branch 的 Eevee 源码给出两条设计依据：

- [`eevee_engine.cc`](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/draw/engines/eevee/eevee_engine.cc) 在每次 image render 中创建新的 `Instance`，结束后删除；
- [`eevee_sampling.cc`](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/draw/engines/eevee/eevee_sampling.cc) 对 image render 的 sample dimension 使用由 sample index 驱动的 Halton sequence；
- [`eevee_instance.cc`](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/draw/engines/eevee/eevee_instance.cc) 在 Metal/Vulkan 的每个 sample 后执行 `GPU_flush()` 与 `GPU_render_step()`；
- Blender 的 [Film module](https://developer.blender.org/docs/features/eevee/modules/film/) 说明 Combined film 会对邻近 render pixels 加权，而 data pass 只保留 closest sample，不做同样的 weighted average。

这些源码事实不能自己解释 B28，但使 Combined × closest-sample data pass × coverage pass 成为可证伪的下一观测。

## pilot 设计

一个真实 Blender 5.2.0 LTS PID 在 frame 38 连续 render 12 次。每次 render 只调用 operator 一次，随后从同一 Render Result 保存 PNG8 与 ZIP multilayer EXR32。EXR 包含 Combined、Depth、Normal、Position，以及源场景已有的 Vector 和三层 CryptoObject。

固定 Eevee 32 samples、dither 0、Fast GI on、TAA reprojection on、FIXED/8 threads。源 `.blend` 未保存。pilot 没有支持阈值、显著性检验或确认性 decision。

## 观察

第 1–11 次 PNG 都是 B28 `REFERENCE` decoded RGB SHA；第 12 次是冻结的 `ALTERNATE` SHA。

- Combined EXR32：第 12 次进入第二 float mode；26 个像素变化，bbox `x=267–272, y=112–117`，最大绝对误差 `0.00390625`；
- CryptoObject00：第 12 次同步进入第二 mode；7 个像素变化，bbox `x=268–270, y=113–115`，最大绝对误差约 `0.01465136`；
- Depth、Normal、Position：12/12 严格 float exact；
- CryptoObject01/02：12/12 严格 float exact；
- Vector：第 1 次相对第 2–12 次出现 full-frame transient，518,255 个像素变化；它没有伴随 Combined/PNG mode 切换。

Cryptomatte manifest 把变化的两个 ID 解码为 `BACK_WALL` (`0f749ae0`) 与 `FLOOR` (`d3249e06`)。7 个变化像素都是这两个对象在墙地边缘的 coverage weight 改变；对象 ID 本身没有变化。变化区域严格落在 B27 的 17-pixel PNG cluster 内。

## 能说与不能说

这一次 pilot 支持一个用于正式验证的更窄模式：`ALTERNATE PNG + Combined float change + BACK_WALL/FLOOR Crypto coverage change + closest-sample Depth/Normal/Position stable`。它也发现了一个与 Combined 脱钩的 first-call Vector transient。

不能据此确认 film resampling、rasterization 或 GPU scheduling 是原因。单一 PID、单一 ALTERNATE event 没有确认性复现，也不能排除启用额外 passes 对 mode 频率的影响。正式 B29 必须在新 PID 中冻结 pass hashes、耦合规则、novel-mode 处理与至少两个独立 PID 的支持阈值。

## 冻结输入候选

- pilot report SHA：`959bde374db3af7276f4db75d73d78717d1a35505213571dcb458ab056359794`；
- pass analysis SHA：`17a3ecb6b826480533f93d1446e399fc0cd1dbd8244aba0a9a46e5517e20bbc2`；
- pilot renderer SHA：`db9674f971e064d1905beff1dd8a2cb8efcd26237da3a30e767659509e390941`；
- pilot analyzer SHA：`28d2a098ad386e5de0d521a11e2ff042f615de3104dbac796dd628b350c541ae`。

Artifacts: `experiments/pass-domain-pilot-v0-1/evidence/pilot.json`, `experiments/pass-domain-pilot-v0-1/pass-analysis.json`, `blender/explore_b29_pass_domain.py` and `blender/analyze_b29_pass_pilot.py`.
