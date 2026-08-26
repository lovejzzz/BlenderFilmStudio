# B29 · frame 38 pass-domain localization protocol

日期：2026-08-26（America/New_York）  
状态：`PRE-REGISTERED · NOT YET EXECUTED`

## 问题

B28 证明同一 PID 内可在两个 PNG mode 之间切换。B29 问一个更窄的问题：在新的 pass-enabled holdout 中，每次 ALTERNATE PNG 是否都同时进入 pilot 冻结的 Combined-float 与 BACK_WALL/FLOOR CryptoObject00 coverage mode，同时 closest-sample Depth、Normal、Position 保持严格一致？

## derivation 与 confirmation 分离

单 PID pilot 是 `EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION`。它选择 pass、hash tuple、coverage 对象和正式阈值，但不能计入 B29 的 12 个 PID。pilot 的 renderer、analyzer、report 与 analysis hash 已冻结在 spec 中。

预注册时，正式文件 `blender/render_b29_pass_domain.py`、`blender/classify_b29_pass_domain.py` 和 `scripts/run-b29-pass-domain.mjs` 均不存在。正式工具将在本协议提交后实现。

## 设计

12 个全新 Blender 进程 P01–P12，每个只设置一次 frame 38，然后连续 render 12 次。每次只执行一次 render operator，并从同一个 Render Result 保存一个 PNG8 与一个 ZIP EXR32 multilayer；总计 144 render、288 save、288 文件。

固定 `.blend`、BuildPlan、structure、ReviewRenderSpec、Blender 5.2 binary、ACES 2 OCIO、32 samples、dither 0、Fast GI、TAA reprojection、FIXED/8 threads、960×540 与无 motion blur。显式启用 Combined、Depth、Normal、Position、Vector 与 Object Cryptomatte depth 6。

## 主分类

- `COUPLED_REFERENCE`：PNG、Combined、CryptoObject00 都命中各自 REFERENCE hash，并且 Depth/Normal/Position 命中稳定 hash；
- `COUPLED_ALTERNATE`：三个 mode-bearing 输出都命中 ALTERNATE hash，并且三个 closest-sample pass 稳定；
- 任意 primary-domain 第三 hash：`PASS_SPACE_EXPANDED`；
- closest-sample pass 变化：`CLOSEST_SAMPLE_PASS_VARIATION`；
- 已知 hash 被重新组合成非冻结 tuple：`DECOUPLED_PASS_PATTERN`。

一个 PID 必须同时包含至少一个 coupled reference 与一个 coupled alternate 才算 supporting process。正式支持阈值冻结为至少两个独立 supporting PID。decision 有明确优先级；novel/data/decoupled 反例优先于支持。

## 次终点

Vector 的 call-1 transient、CryptoObject01/02 稳定性、mode 按 PID/ordinal 的频率、Combined/CryptoObject00 数值差、bbox 与 wall/floor coverage 都保留。但 Vector pattern 不替代主终点，也不能用 144 个相关 render 假装 144 个独立进程。

## 非主张

即使主结果支持，也只能把事件定位到带权 Combined/Crypto coverage，而不能直接把原因命名为 film filter、rasterizer、Metal、TAA 或 GPU race。Depth/Normal/Position exact 只约束本 frame/profile 的 closest-sample outputs。机器 pass 不回答肉眼可见性或电影感；B26 人类门保持独立 `PENDING`。

正式规范：`specs/pass-domain-localization-spec.v0.1.json`。
