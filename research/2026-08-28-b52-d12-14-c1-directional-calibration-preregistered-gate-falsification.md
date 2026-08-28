# B52-D12.14-C1：预登记投影门在正式运行前被 Blender 5.2 精度反例证伪

Date: 2026-08-28  
Classification: `PREFORMAL_DESIGN_FALSIFICATION`  
Formal output root created: **no**  
Blender renders / EXR / model calls / network calls: **0 / 0 / 0 / 0**

## 结论

`B52-D12.14-C1` 的搜索思想在两个独立 scalar implementations 中能够稳定构造目标投影域，但原预登记把 Blender corner-projection maximum absolute error 冻结为 `1e-9 pixel`。真实 Blender 5.2 factory-empty projection probe 在三个临时候选上分别产生约 `5.0e-6–5.8e-6 pixel` 的误差，因此该硬门在当前 Blender/mathutils 几何表示路径上不可满足。

这不是正式实验的失败结果：五个工具没有全部实现或冻结，formal root 从未创建，临时输出已经清除。它是对实验设计本身的预正式反例。原 spec 必须保持原字节与哈希，不能把 `1e-9` 事后改成较宽容的阈值再称为同一次预登记。

## 临时、非正式观察

Python 与 Node scalar oracle 各自枚举冻结的 3,900 个候选，并对 candidate table 和 selected masks 达到 byte exact。两者都临时选出：

- `TOP-000000`：109 个 target witnesses，0 个 non-target one-sided witnesses；
- `BOTTOM-000000`：109 个 target witnesses，0 个 non-target one-sided witnesses；
- `NEITHER-001212`：4,071 个 target witnesses，0 个 non-target one-sided witnesses。

这些选择来自未冻结工具的 `/tmp` smoke，不能成为结果、fixture 或后续 holdout 输入。

三个真实 Blender 5.2 zero-render probes 的 maximum absolute pixel error：

| Target | Blender projection | Independent scalar projection | Render Result |
|---|---:|---:|---|
| TOP | `5.7220458984375e-6` | `7.105427357601002e-15` | absent |
| BOTTOM | `5.781650543212891e-6` | `1.4210854715202004e-14` | absent |
| NEITHER | `5.0067901611328125e-6` | `1.4210854715202004e-14` | absent |

Scalar projection接近 binary64 roundoff，而 Blender path 的误差量级与 mathutils/mesh coordinates 的 float representation 相符；这是一项机制推断，不是对 Blender 内部实现的源码证明。

## 第二个尚未满足的边界

NEITHER 临时候选需要约 `58.5366×` 的水平投影尺度差。投影矩形 oracle 可以表达该差异，但当前 Blender probe 分别反解两帧矩形，没有证明两帧来自同一尺寸的刚体平面。D12.12-H1 使用近 edge-on → face-on 旋转试图建立这种尺度差，因此下一设计必须直接搜索同一刚体平面的世界变换与透视投影，而不能把两个独立矩形当作已经可实现的 Blender fixture。

## 下一步约束

1. 保留 `B52-D12.14-C1` spec 与本反例；不得生成它的 formal result 或 receipt。
2. 若只研究 projected-domain construction，必须用新的实验 ID 明确把结论限制为 raster-domain target，不得称为 Blender rigid fixture。
3. 在任何 fresh render holdout 之前，另行预登记 rigid-realizability calibration：固定同一 owner 尺寸，枚举 camera/owner XYZ transforms 与 Euler rotations，由两个独立 3D projection/ray-plane implementations 和 Blender RNA probe共同验证。
4. Blender projection tolerance 必须基于这次已披露的 preformal observation 另行冻结，并保留充分但有限的量化裕量；不能改写原来的 `1e-9` 门。

## 可复核身份

- Preregistered spec SHA-256: `fd3fe2808346c49a87183b3ed215b07abcbaf4058df13d055cc893b482ae30f5`
- Preregistered commit: `9b20091`
- Blender executable SHA-256: `60ba7a9b6743f7acf101274361fa76409e382ae07cd2007ce07dea30f6b129f2`
- Blender: `5.2.0 LTS`, build `fbe6228777e7`
- Temporary candidate-table SHA-256 (Python and Node exact): `97920657e2c1c4663dfe04866bcc93a1ba9f6a1eb91740561cb7cebba5908ff9`

The temporary output directory was deleted after the measurements. The prototype source is retained separately as non-formal algorithm history.
