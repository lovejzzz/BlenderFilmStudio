# B34 result · NATURAL / Q4 / Q8 independent-human review package

日期：2026-08-26（America/New_York）

Package 判定：**`CARRIER_AND_INTERFACE_READY`**

人类证据状态：**`HUMAN_REVIEW_PENDING` · 0/18**

这两个状态不能合并：B34 已证明正式载体、盲法、响应验证与分析边界可运行，但没有证明观察者偏好、可见闪烁差异或电影感。

## 预注册与工具冻结

- 协议和机器可读 spec 在任何 B34 工具或输出之前提交：`9224bd9`；
- spec SHA-256：`4afcb29f9d47671d4696d0b6d57f5d7e0c5fde4f08bee1e414040ed480257ba2`；
- renderer、scene-linear compositor、display exporter、carrier builder、observer UI、response validator、append-only ledger 与 formal analyzer 随后提交：`432e6b2`；
- 独立审计器在审计输出之前提交：`c981ac0`，首轮报告字段 bug 修复后工具提交为 `00cc6a6`。

正式主问题只有 Q8 对 NATURAL32 的时间稳定性方向判断；Q4 是诊断性成本点，不能改变主判定。18 名有效独立观察者必须覆盖六种顺序各三人。远程受控记录参考当前 ITU-R BT.500-15，但不是校准实验室实现。

## 真实 Blender 执行

运行时为 Blender 5.2.0 LTS build `fbe6228777e7`，binary SHA `60ba7a9b…129f2`，固定 OCIO SHA `24ec8184…ad15`，scene SHA `2a505360…1b0b`。

- 13 个唯一 Blender PID；
- frame 1–144，24 fps，960×540，motion blur off；
- NATURAL32：144 renders / 144 EXR；
- Q4：576 renders / 576 EXR；
- Q8：1,152 renders / 1,152 EXR；
- 合计 1,872 次真实 render / 1,872 个 fresh float32 EXR；
- 源渲染时间：NATURAL `24.378508 s`，Q4 `96.557780 s`，Q8 `194.590571 s`，总计 `315.526859 s`；
- scene-linear ACEScg 合成/显示导出：432 EXR + 432 PNG，`62.371250 s`。

旧 B33 数据上的提交后 smoke test 先验证了 compositor：Q4 输出与独立 NumPy 均值最大误差 `0.0`；PNG 为 960×540 RGBA uint8 且 alpha 全不透明。另一个 non-empty-directory attack 在写出任何 EXR 前退出，观察到预期错误 `B34 source output directory must be empty`。

## 三条真实载体

三个方法统一经过 `sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709) / None / exposure 0 / gamma 1 / dither 0`，编码为 lossless VP9 Profile 1 `gbrp`：

| 方法 | WebM bytes | SHA-256 | fresh decode RGB exact |
|---|---:|---|---:|
| NATURAL32 | 27,491,693 | `7d09a539…071d8` | 144/144 |
| Q4 | 25,417,613 | `76c97538…2fed0` | 144/144 |
| Q8 | 24,463,879 | `919b8c3d…4149c` | 144/144 |

三条载体最大 RGB 误差均为 `0`，改变 RGB 像素总数为 `0`。审计阶段重新从 WebM fresh decode 到另一目录，三个 roundtrip report 分别与正式报告 byte exact 同哈希：`42114267…1b78`、`bd232ed0…ee`、`5c323692…2cb`。

## 盲法、响应链与攻击

- 18 个 salted session；六种 NATURAL/Q4/Q8 顺序各三份；
- overall mapping commitment：`dddb0915…5b20`；
- observer package 只有 `CLIP-01/02/03` 与 carrier hash，不含 underlying mapping；
- primary player 无 native controls，要求每条完整播放两次；
- response 绑定 spec、mapping commitment、carrier、逐次 playback telemetry 与 canonical response hash；
- accepted response 使用 exclusive-create 文件与 JSONL append-only ledger；先锁 response 才允许 analyzer 解盲。

24/24 冻结攻击按预期拒绝，包括 spec/runtime/source 置换、PID 重复、合成/显示变化、carrier metadata/RGB 回环、盲法泄漏、播放掉帧、显示器条件、开发者计入、response mutation、提前解盲、重复 observer、18 人以下误跑正式决策，以及 Q4 副终点改变主结论。

synthetic analyzer fixture 故意把 18 人的 Q4 都设为 `SEVERE`、主比较都设为 indistinguishable；分析器仍给出预期主判定 `NO_DIRECTIONAL_DIFFERENCE_OBSERVED_UNDER_TEST_CONDITIONS`。它的分类明确是 `ATTACK_TEST_ONLY_NOT_HUMAN_EVIDENCE`。

## 独立审计与保留的失败

独立 package audit 首次运行在写最终 JSON 前因变量名错误失败：内部累计变量是 `changedPixels`，报告字段错误引用 `changedRgbPixels`。该失败没有改写成成功；修复提交 `00cc6a6` 后从头重跑。

重跑结果：

- 1,872/1,872 源 EXR 文件、顺序与 SHA 通过；
- 432/432 composite EXR 与 432/432 display PNG SHA 通过；
- 432/432 carrier roundtrip frame 绑定通过，changed RGB pixels `0`；
- 18/18 session commitment、hard-linked carrier 与无 mapping 泄漏检查通过；
- 独立 Blender 重算全部 432 个 composite：最大 float error `0.0`、changed float values `0`；第二个 factory-startup 进程输出 byte exact。

## 浏览器 interface pilot

本机真实浏览器在 1920×1080 / DPR 1 下验证：document 无横向溢出，video CSS 为 960×540，native controls `false`，页面 HTML 无 underlying method 字符串，console error 为 0。NATURAL/Q4/Q8 的实际映射没有用于主观判断。对 CLIP-01 完整播放两次，每次 telemetry 都是 decoded `144`、dropped `0`；第二次结束前评分字段保持 disabled，之后才解锁。

这是开发者 interface pilot，formal response count 仍为 0。

## 当前边界

B34 现在消除了“没有正式可分发载体/验证器/分析器”的工程缺口，但没有消除最关键的证据缺口：18 名独立观察者尚未完成。package ready 不能被写成 Q8 更好、无差异或有人类支持。远程显示器不统一；结果即使完成也只适用于这组三条六秒载体与记录条件。motion blur、4K 投影、跨镜头/机器、交付编码、表演、叙事和整体电影感仍不在声明内。

## 证据

- `experiments/human-quadrature-review-v0-1/results.json` · SHA-256 `372a898facde229faf24e6cf04b37783406d4c4ecf80e47855c9954f9bdda071`
- `experiments/human-quadrature-review-v0-1/evidence/package.manifest.json` · SHA-256 `df12706646b0c893b0e8a5a8ef0858e1f3d831400154c59d754bdd20eb9276f7`
- `experiments/human-quadrature-review-v0-1/evidence/composite-display.manifest.json` · SHA-256 `9e57c81716c5bd77eeae6fc12c0b28e8628894491db4bc0cc7375762d5400507`
- `experiments/human-quadrature-review-v0-1/evidence/independent-package-audit.json` · SHA-256 `65dbfb2836fa852b76f2d143c88cbecbc1fc77b0d52ed9372637915b3f375e07`
- `experiments/human-quadrature-review-v0-1/evidence/independent-composite-audit.json` · SHA-256 `7317be38d41119306e3589aa56244355d41fed638e7ab347a0acfc28b1f2df54`
