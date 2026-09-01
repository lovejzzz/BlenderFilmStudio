# PC4-VU1：视觉理解到受限改进计划 PASS

状态：`PASS`。这是一项软件能力结论，不是 PC.4 画面质量 PASS，也不替代仍待用户填写的 PC.3 human review。

## 结果

PC4-VU1 把 PC.4 attempt-03 的三张代表帧、场景 SHA、镜头与实体清单组成严格的 `VisualReviewPacket`；把截图视觉判断写成带画面区域、实体引用、类别、严重度、置信度与语义 treatment 的 `VisualAssessment`；再由确定性编译器生成 `VisualImprovementPlan`。

接受的 plan hash 为 `674bc0820eb1856539cc310e628bb69b32ee6ae8b88d7d4662d9deff27d7ac00`。它包含六项按优先级排列的受限操作：

1. 清除 wide 中已确认的 chamber ring 与 column 遮挡；
2. 重构 medium framing；
3. 增加 close face segmentation；
4. 将 medium 的球形肩肘读感替换为 layered mechanical joint；
5. 重构 close framing；
6. 为 torso 与 helmet 增加 mid-scale panel hierarchy。

计划同时把现有的 cinematic lighting 与 wide/medium/close camera language 写成必须保留的两个 strength invariants。它只表达语义操作，不包含 Python、shell、网络、任意路径或 Blender operator 权限。

## 证据

正式 attempt-03 位于 `experiments/visual-understanding-loop/PC4-VU1-2026-08-31-attempt-03`：

- 两次编译 canonical bytes exact；
- 19/19 contract tests PASS，覆盖低置信度 defer、未知 frame/entity、错误 treatment、越界 region、代码/网络夹带和 self-hash tamper；
- 独立审计 20/20 PASS，audit self hash `eb853d067d43c0cd02843d679215de9a19d48536471ccfb7e69c7b162b84718f`；
- receipt self hash `b72a63548fa0d10d3b8630b74927bc3eea47186ab5c8a576312e11bcbc2b58c6`；
- 0 Blender start、0 render、0 scene mutation、0 network call、0 model call during compiler execution。

Attempt-01 在 root 创建前因 missing parent 停止且无 root；attempt-02 已生成 plan/receipt，但独立审计器错误地把 TAP 当 JSON，保留为 harness failure。C1/C2 没有改变 schema、教学答案、编译器核心或阈值。

## 已证明与未证明

已证明：软件可以接收一份视觉老师的结构化判断，验证它是否有图像与场景证据，拒绝越权内容，并稳定编译为可审计的改进计划。

尚未证明：软件能自动选择所有最佳代表帧、视觉模型能在未见作品上稳定达到同等判断质量、typed executor 能正确修改 `.blend`，以及计划执行后画面一定更好。下一步是实现只消费这六类语义 operation 的 typed executor，在当前真实项目生成新截图，再由同一套 review loop 做 A/B 回归。

