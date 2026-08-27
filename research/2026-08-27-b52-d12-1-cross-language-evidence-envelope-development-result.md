# B52-D12.1-DEV · typed evidence envelope 开发结果

日期：2026-08-27  
结果：`DEVELOPMENT_TYPED_EVIDENCE_ENVELOPE_NOT_COMPATIBLE`  
Blender/model/network calls：0/0/0

## 结论

IEEE-754 typed envelope 解决了“同一份 JSON 在两个语言中如何得到同一 hash”的问题，但没有解决“两个语言独立计算的派生指标是否逐 bit 相同”的问题。因此开发合同按预注册规则失败。

Python 与 Node encoder 对全部 16 份 report body 都产生逐字节相同的 envelope 和 SHA-256；对每份 report 的 `measurements` 子树也分别一致。16/16 adversarial cases 通过，包括 signed zero、safe integer、nonfinite、surrogate、key order 与 array order。

然而，把对应 Python/Node reconstructor 的 measurement envelope 互相比对时只有 4/8 cells 完全相同。失败集中在两类派生 reduction：

- `PROJECTIVE_CAMERA_DOLLY_YAW_107X67` 的两个 repeats：wrong-sign RMSE 相差 `1.50227e-15`，PSNR 相差 `5.15143e-13 dB`；
- `PROJECTIVE_STATIC_CONTROL_107X67` 的两个 repeats：Vector endpoint p99 相差 `1.69407e-21 px`，即一个 binary64 ULP。

这些差异不会改变 D12 的任何 gate，且底层八类 float32/u8 arrays 仍为 8/8 byte-identical。它们来自 Python/NumPy 与 JavaScript reduction/quantile 的浮点求和和插值路径，而不是 JSON 序列化。

## 工程含义

未来 evidence schema 应分离三层身份：

1. **payload identity**：原始 float32/u8 arrays 必须逐字节相同；
2. **document self-integrity**：每个 producer 自己的 report 可用 typed envelope 被任意语言重新验 hash；
3. **decision metrics**：由一个冻结的独立 analyzer 从 payload 重算，不要求两个 producer 的派生 reduction 逐 bit 相同。

若必须比较 producer metrics，应预注册绝对/ULP 容差与 reduction 顺序，而不是把它们误称为 payload identity。下一个 fresh holdout 需要测试上述三层模型；不能回改 D12 或把本开发负结果重新标成 compatible。

## 证据

- result SHA-256：`4fc177c51060d035b02384c4d7aa1c9e427394c5589e7bddfd9102553008ce07`
- internal result hash：`ec8b57dcacde07c5741b3ec5d5a300551ec4557e18a72106bae467a54f8826de`
- gates：10/11
- encoder processes：50 Python + 50 Node
- source reports modified：0
- output：`experiments/blender-cross-language-evidence-envelope-development-v0-1/results.json`

## 非结论

- 不修改 D12 `NOT_SUPPORTED` 或其 C2 audit `PASS`。
- 不证明 RFC 8785/JCS 合规。
- 不支持在未知算法间任意放宽浮点 metric 比较。
- 不涉及 Blender 渲染、时序画质或生产场景。
