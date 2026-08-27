# B52-D6 · 独立确定性 Displace 校准结果

日期：2026-08-27

## 结论

正式结论是 `DETERMINISTIC_DISPLACE_CALIBRATION_NOT_SUPPORTED`，最早失败为 `REFERENCE_MATCH`。

这不是“Blender Displace 不可用”。更准确的结论是：在预注册的七个 primitive 中，六个与独立 CPU 参考逐 float32 完全一致；唯一的 Bilinear subpixel fixture 跨两个净进程稳定复现，但没有达到预注册的逐位完全一致门。因此 D6 不能把“包含 Bilinear 的完整集合”提升为 exact oracle。

## 正式运行边界

- Blender：5.2.0 LTS，build hash `fbe6228777e7`；
- compositor：CPU，固定 1 线程；
- 14 个全新 Blender 进程，14 个唯一 PID；
- 14 次 compositor render，0 次 Cycles ray render；
- 7 个 fixture × 2 个净进程重复全部 decoded exact；
- 20/20 adversarial attacks；
- 独立 audit：`PASS`；analyzer 重放逐字节完全一致；14/14 run artifact、35/35 derived artifact 通过。

## 测量

| Fixture | 两重复 | 对独立参考 | 最大误差 | RMSE | 越过 1/65536 的像素 | 敏感性 |
|---|---:|---:|---:|---:|---:|---:|
| ZERO_NEAREST_CLIP | exact | exact | 0 | 0 | 0 | pass |
| POSITIVE_INTEGER_NEAREST_CLIP | exact | exact | 0 | 0 | 0 | pass |
| NEGATIVE_INTEGER_NEAREST_CLIP | exact | exact | 0 | 0 | 0 | pass |
| SUBPIXEL_BILINEAR_CLIP | exact | **not exact** | 1.758337e−6 | 4.569772e−8 | 0 | pass |
| DESTINATION_STEP_NEAREST_CLIP | exact | exact | 0 | 0 | 0 | pass |
| POSITIVE_INTEGER_NEAREST_EXTEND | exact | exact | 0 | 0 | 0 | pass |
| POSITIVE_INTEGER_NEAREST_REPEAT | exact | exact | 0 | 0 | 0 | pass |

全部六个非零任务都有 3,071 或 3,072 个像素越过敏感性门，最大变化为 0.58203125–1.0；不存在“两个空实现相等”的退化。

## Bilinear 反例的形状

正式 R1/R2 的 Bilinear 输出 decoded hash 完全相同，说明差异不是净进程随机性。相对独立参考共有 341 个非零 scalar、188 个非零像素；全部像素误差仍低于 `1/65536`。全数组 p99 为 `1.192093e−7`，最大值位于 decoded `(y=18,x=14,B)`，Blender 为 `0.2695294917`，参考为 `0.26953125`。alpha 最大误差为 0；只有 6 个非零像素位于图像外边界。

测量事实只说明 Blender 的 Bilinear 输出与我们冻结的 NumPy float32 运算次序不逐位相同。一个合理但尚未验证的推断是内部滤波精度、权重计算或运算次序不同；D6 不把该推断写成原因。

## 可以保留什么

D6 已经提供强证据支持以下窄结论：在绑定的 Blender 5.2 build、CPU compositor 与 analytic raster 上，零位移、正负整数 Clip、目的采样 step field、Extend 和 Repeat 六个 Nearest primitive 都与独立参考逐 float32 相同，且跨净进程复现。

但按预注册规则，不能把这六项局部通过改写成整个 D6 的 `SUPPORTED`，也不能在看过 Bilinear 输出后把 exact 门改成 tolerance 门。

## 下一步

下一项必须是新预注册、fresh-output 的 subpixel holdout：使用未见过的位移、不同 alpha/频率结构与至少两个分辨率，冻结 `1/65536` tolerance（该阈值在 D6 输出前已经存在），验证误差是否稳定受界、是否存在系统性偏移，并与一个第二独立采样实现交叉检查。只有通过后，才允许进入 depth/layer-aware temporal accumulation。

## 身份

- receipt SHA-256：`728c5b4402e86801f376db45184895e4393f97422e140fa0cbeaf8a9433333ce`
- result SHA-256：`e473ead8715b34971f7d457b86c0821782504ed22ae321eba5f9843ca9fe0348`
- result self-hash：`8eed8e37b4261d59a75b1edb9ed48c7a6c363f551394e776bc50ed42ef198160`
- evidence core：`ff59d101b269bf1963791968ed3737f8d030677b6566b2f9e889e692b591256b`
- audit SHA-256：`3f50e7e01a50946aead0aee4924a9f12e960989640d365e6c6b31c8e732976af`

Artifacts: `experiments/deterministic-displace-calibration-v0-1/`.
