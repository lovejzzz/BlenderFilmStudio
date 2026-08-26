# B29 · frame 38 pass-domain localization result

日期：2026-08-26（America/New_York）  
预注册提交：`e22e58e`  
首个正式工具提交：`a7fa8cc`  
接受的 runner 修正提交：`d095ff0`  
冻结判定：`DECOUPLED_PASS_PATTERN`

## 工具候选失败与全量重跑

第一批 12 个进程和 144 次 render 完成后，runner 在晋级前把实验判为 invalid：report 的 `passState` 正确显式记录 9 个字段，但 validator 错写为 8。没有修改预注册 spec、hash tuple、样本数或 decision。validator 修正为 9 后提交，第一批输出全部作废，随后用 12 个新的 PID 完整重跑，而不是复用已经看过的 render。

## 正式结果

接受批次完成 12/12 unique PID、144 render、288 same-Render-Result saves、144 PNG8 与 144 multilayer EXR32。分类为：

- `COUPLED_REFERENCE`：103/144；
- `COUPLED_ALTERNATE`：38/144；
- `DECOUPLED_PASS_PATTERN`：3/144；
- novel primary hash：0；
- closest-sample Depth/Normal/Position variant：0；
- 25/25 个冻结攻击达到预期拒绝原因。

10/12 个 PID 同时含 coupled reference 与 coupled alternate，超过 ≥2 的支持阈值。但预注册规则明确让任何 decoupled tuple 优先于支持，因此最终结果必须是 `DECOUPLED_PASS_PATTERN`，不能写成 `COVERAGE_COUPLED_LOCALIZATION_SUPPORT`。

## 三个反例

P01 call 4、P03 call 8、P04 call 5 都是同一个解耦 tuple：

- PNG decoded RGB：REFERENCE；
- Combined EXR32：REFERENCE；
- CryptoObject00：ALTERNATE；
- Depth / Normal / Position：全部为冻结 stable hash。

因此 CryptoObject00 的 wall/floor coverage mode 可以在 Combined 与最终 PNG 不切换时独立进入第二状态。在 144 次正式输出中，38 个 Combined ALTERNATE 都伴随 Crypto ALTERNATE，但另外还有 3 个“Crypto-only alternate”。这是观测到的包含关系，不是因果证明；Crypto alternate 在此数据中不是 Combined alternate 的充分条件。

## 仍然被确认的层

PNG 与 scene-linear Combined 在 144/144 次中 mode 标签一致，进一步确认差异在 PNG 编码前已存在。Depth、Normal、Position 144/144 严格 float exact，说明这个 event 没有表现为这些 closest-sample pass 的位置/法线/深度变化。

两个完整 mode 的数值差与 pilot 完全一致：Combined 26 个 float pixels，bbox `x=267–272, y=112–117`，最大绝对误差 `0.00390625`；CryptoObject00 7 个 coverage pixels，bbox `x=268–270, y=113–115`，最大绝对误差约 `0.01465136`。Cryptomatte ID 仍是 `BACK_WALL` 与 `FLOOR`，变化的是 coverage weight。

Vector 的 first-call transient 在 12/12 PID 中按 pilot 冻结模式复现：call 1 一个 hash，call 2–12 另一个 hash。CryptoObject01/02 也在全部输出中稳定。Vector transient 与 Combined mode 解耦，保持次终点身份。

## 结论边界

B29 否证了“Crypto coverage mode 与 Combined mode 总是一一耦合”的确认性假设。它保留了更窄事实：Combined/PNG mode 一致；closest-sample geometry passes 稳定；CryptoObject00 coverage 有一个包含全部 Combined alternate、但还额外出现三次的第二模式。

不能据此命名 film resampling、rasterization、Metal、TAA 或 GPU scheduling 为原因，也不能说 geometry globally deterministic。启用 diagnostic passes 形成自己的冻结 profile，频率不能直接与 B28 合并。机器 pass identity 仍不回答可见性或电影感；B26 human review 保持 `PENDING`。

## 下一边界

Blender 5.2 `Sampling::init` 暴露了未进入普通 UI 的 scene custom property `override_pixel_jitter_sample`。下一步可把它作为机制 probe：在新对照样本中固定 filter jitter position，比较自然 Halton filter jitter 与固定 jitter 下 Combined/Crypto repeatability。由于固定单一点会改变抗锯齿采样目标，它只能作为机制干预，不能直接当生产修复。候选值和对照输出必须先做 derivation，再预注册正式 holdout。

Artifacts: `experiments/pass-domain-localization-v0-1/results.json`, `experiments/pass-domain-localization-v0-1/evidence/`, `specs/pass-domain-localization-spec.v0.1.json` and `research/2026-08-26-b29-pass-domain-localization-protocol.md`.
