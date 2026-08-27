# B52-D12-C1 · 完整正式结果与首次审计失败

日期：2026-08-27  
矩阵状态：`COMPLETE_65_UNIQUE_CHILD_PIDS`  
冻结 analyzer verdict：`BLENDER_PROJECTIVE_SUBPIXEL_RECONSTRUCTION_HOLDOUT_NOT_SUPPORTED`  
最早失败 gate：`DUAL_RECONSTRUCTION_IDENTITY`  
首次独立 audit：`FAIL`（保留）

C2 corrected audit：`PASS`

## 结论先行

C1 的基础设施更正成功：新根目录从零完成了全部 16 次 Cycles source、8 次 adapter、16 次双语言 reconstruction、8 次 encoder、16 次 Blender compositor bridge 和 1 次 analyzer，共 65 个唯一子 PID。没有读取失败 D12 根目录中的任何测量输入。

冻结的 D12 合约仍返回 `NOT_SUPPORTED`。最早失败不是 Vector 方向、投影公式、双线性数值、深度预测、动态画质或 Blender bridge，而是 Node report 的跨语言 canonical self-hash。Python 和 Node 的八类数组在 8/8 cells 中逐字节相同，也都与 analyzer 的独立重建逐字节相同；但是 JavaScript 将约 `1e-5` 的数写成小数，Python canonical JSON 写成指数形式，因此 Python 的 `valid_report()` 拒绝所有八份 Node report。

另一个独立失败是真正的静态“绝对精确”边界。静态 Vector 最大残差为 `1.5258789e-5 px`，仍低于 Vector 的 `1/1024 px` gate，但不等于零。双线性采样因此产生最大 `1.4901161e-7` RGB 误差，而冻结阈值要求 `staticReconstructionMaximumRgb = 0.0`。这使 `STATIC_CONTROL` 与汇总的 `RECONSTRUCTION_QUALITY` 为 false。

## 运动场景的测量事实

| fixture | valid pixels | endpoint max (px) | correct RMSE | PSNR | nearest RMSE | wrong-sign RMSE | direct-depth rejected |
|---|---:|---:|---:|---:|---:|---:|---:|
| object dolly/translate | 5,841 | `2.2173e-5` | `5.0454e-5` | 85.94 dB | `2.2481e-3` | `1.7631e-2` | 100% |
| object yaw/pitch | 5,841 | `3.9756e-5` | `4.5846e-5` | 86.77 dB | `2.2893e-3` | `9.9056e-3` | 96.39% |
| camera dolly/yaw | 5,841 | `4.0770e-5` | `3.9260e-5` | 88.12 dB | `2.3696e-3` | `2.5166e-2` | 100% |

两次 source repeat 的数值完全相同。三个运动 fixture 都通过 endpoint、亚像素域、transform-aware depth、绝对 RGB 质量、nearest/wrong-sign sensitivity 和 direct-depth counterexample 门。上述事实不能覆盖冻结 verdict，但它们明确缩小了下一步：投影/Vector/双线性/深度物理不是此次拒绝的原因。

## 为什么首次 audit 也必须保留为 FAIL

首次 audit 文件不是科学 verdict 的替代品。它有两个失败检查：

1. 我用相对 `--formal-root` 调用冻结 audit；正式 analyzer 写入 sidecar 时使用绝对根目录，replay 因 URI 字符串不同而在第一份 sidecar 停止。
2. 冻结 audit 的 `attackTotality` 要求 57/57 attack 全部为 true。这对 supported 结果成立，但对合法的 negative result 不成立；本次十个与 report identity、quality 和 static gate 对应的 attack 正确地为 false。

一个不写入正式根目录的诊断 replay 使用绝对根目录后，`evidenceReplay`、身份、进程、诊断和 verdict consistency 全部通过，唯一剩余失败就是上述 `attackTotality` 定义。这是 audit-only 工具缺陷；该临时诊断输出已删除，不能充当正式 audit。

随后预注册并冻结的 audit-only C2 将 formal root 规范化为绝对路径，并把 attack totality 检查改为“57 个注册项完整、顺序一致、布尔值与计数一致”，而不是要求负结果的每个 gate 都通过。C2 只运行一次继承 analyzer 的 verify replay，没有 Blender 进程或正式数据改写。

C2 结果为 `PASS`：10/10 checks 为 true，replay 退出 0，并逐项复现 evidence、measurements、24 份 diagnostics、operation counts、57 个 attack 布尔值、47 的通过计数、negative verdict 与 `DUAL_RECONSTRUCTION_IDENTITY` base failure。C2 不改变原 `FAIL` audit，也不把任何 false gate 改为 true。

## 证据身份

- formal root：`experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/`
- receipt SHA-256：`8c78b88ef512a5f7aa39554fced1067c12a5a0036c4c8231964b544da146ea4b`
- result SHA-256：`a411948ec8854029d199786bbf0a81565bc91099e2f973a2311b7513c2d07d82`
- failed audit SHA-256：`f090b7667f7ea882cc45df694f0d1dd0e39a2ead3bc83cde268b7990a64f832d`
- C2 passing audit SHA-256：`8496c264fff4f9eca48ab9ac2bdb751b9d39f7124215da856829104550cb0481`
- C2 internal audit hash：`603c5b31ddb9e9530dc993bb3cd043dce3a3e75d4736821949a093e015f13865`
- frozen result attacks：47/57 passed
- diagnostics：24 PNG + 24 bound sidecars
- formal root size at retention：约 17 MiB，477 files

## 非结论

- 这不支持曲面、变形、遮挡、多 owner、透明、毛发、体积、运动模糊、景深、噪声光照或生产级时序积累。
- 数值很小不等于 static exact gate 通过；该 gate 按预注册规则确实失败。
- Node 数组相同不等于 Node report identity 通过；冻结合约把两者同时放进最早的 dual identity gate。
- C2 `PASS` 确认的是冻结负结果的可重放性，不支持被 D12 排除的生产范围。
