# B34 protocol · independent human review of NATURAL / Q4 / Q8

日期：2026-08-26（America/New_York）

状态：`PREREGISTERED_BEFORE_CARRIER_TOOLING_OR_OUTPUTS`

机器可读实验契约：`specs/human-quadrature-review-spec.v0.1.json`；SHA-256：`4afcb29f9d47671d4696d0b6d57f5d7e0c5fde4f08bee1e414040ed480257ba2`。后续工具、输出、session 与人类响应必须直接绑定这个字节级哈希；若实验设计改变，只能建立新版本，不能静默改写本文件或 v0.1 spec。

## 为什么 B26 不能直接回答 B33

B26 的 lossless carrier、salted mapping 和无 seek/pause primary interface 已经实证可用，但它的 A/B/C 是 B25 的三个 NATURAL32 重复序列。它没有 NATURAL/Q4/Q8 方法比较，也没有正式 response validator、accepted ledger 或 unblinded analyzer。现状仍是 0/18 human responses。

B34 复用经过攻击测试的载体与盲法结构，不复用 B26 内容、mapping 或 session。主问题只冻结一个：独立观察者是否在 Q8 与 NATURAL32 之间给出方向一致的 temporal-stability preference？Q4 是诊断性中间成本点，不允许改变主判定。

## 标准边界

截至 2026-08-26，ITU 官方目录仍将 [ITU-R BT.500-15](https://www.itu.int/rec/R-REC-BT.500-15-202305-I/en) 标为 in force (Main)。B34 记录观察者、显示器、观看距离、环境、播放器与视觉筛查，并采用 18 名独立观察者目标；但这是 remote controlled-record study，不具备校准实验室与统一显示器，因此不能写成“BT.500 compliant laboratory test”。

## 全新六秒载体

正式 carrier source 固定为 frame `1–144`、24 fps、960×540、motion blur off：

- NATURAL32：1 个 fresh PID、144 renders；
- Q4：4 个固定 jitter component PID、576 renders；
- Q8：8 个固定 jitter component PID、1,152 renders；
- 合计 13 个唯一 PID、1,872 个全新 float32 EXR。

Q4/Q8 只在 scene-linear RGB 中按冻结等权平均。三个方法统一通过 `sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709) / None / exposure 0 / gamma 1 / dither 0` 输出 PNG8，再独立编码为 lossless VP9 Profile 1 `gbrp` WebM。每个 carrier 必须完整解码 144 帧并与源 PNG RGB pixel exact。

这是一组冻结 realization，而不是全片 A/B repeatability 实验。B33 的 exact evidence 是采用该方法的依据，不能冒充 B34 全 144 帧的独立重复。

## 资源与保留

渲染前磁盘可用空间必须至少 8 GiB，所有 work 目录必须为空。component EXR 至少保留到 package result、manifest、composite 与 carrier hashes 提交；之后若清理 ignored raw work，必须单独记录删除范围与可由哪个冻结提交重建。

## 观察者与播放

- 目标 18 名有效、未直接参与系统开发的独立观察者；六种方法顺序各三人。
- 三个 clip 各完整播放两次，1×，primary session 无 pause、seek、loop 或速率控制。
- 正式显示器至少 1920×1080，browser zoom 100%，视频 CSS 尺寸 960×540。
- 刷新率必须是 24 的整数倍；接受 48/72/96/120/144/240 Hz。
- 每次播放记录 `totalVideoFrames` 与 `droppedVideoFrames`；任何 dropped frame 使该 session 无效。
- 建议约三个画面高度观看距离，dim/stable ambient；全部实际条件进入 response。

显示器与环境不统一，所以即使 18 人完成，结论仍只适用于记录条件。

## 主判定与副终点

主比较只有 Q8 vs NATURAL32：

- 18 人中至少 14 人方向性选择 Q8 更稳定，且 Q8 的 MILD-or-worse 人数不高于 NATURAL → `Q8_TEMPORAL_PREFERENCE_SUPPORT`；
- 对称条件支持 NATURAL → `NATURAL_TEMPORAL_PREFERENCE_SUPPORT`；
- 至少 14 人选 indistinguishable，且两种主方法各自 MILD-or-worse 不超过 2 人 → `NO_DIRECTIONAL_DIFFERENCE_OBSERVED_UNDER_TEST_CONDITIONS`；
- 其余 → `OBSERVER_DISAGREEMENT`。

1–14 名有效独立观察者只能 `INFORMAL_REVIEW_ONLY`；15–17 为 `FORMAL_REVIEW_INCOMPLETE`；必须 18 名且顺序平衡才运行正式规则。Q4 评级和 pairwise 结果只描述，不参与主决策。

## 响应证据链

每个 observer 下载一个 canonical-hashed immutable response JSON。validator 必须绑定 spec、session commitment、carrier hashes、完整 viewing record、播放遥测与 response hash。accepted ledger 只追加匿名 response hash，不覆盖既有记录。单个 response 先锁定，才允许为分析读取其 sealed mapping；未使用 session 继续保密。

## 非声明

package ready 不等于有人看过；开发者 pilot 不计入正式样本；远程结果不等于实验室结果；motion blur、4K 投影、编码交付、跨场景/机器以及整体电影感都不在本轮声明内。

## Freeze statement

本提交时，B34 renderer、scene-linear compositor、display exporter、carrier builder、response validator、formal analyzer 与任何 B34 EXR/PNG/WebM/session 均不存在。
