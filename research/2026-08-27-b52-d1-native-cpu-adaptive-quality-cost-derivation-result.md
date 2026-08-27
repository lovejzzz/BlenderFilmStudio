# B52-D1：native CPU adaptive quality–cost 派生结果

日期：2026-08-27

状态：`INVALID · FIXED128_PARENT_CONTROL`

正式运行：30 个 fresh Blender 5.2 LTS / native arm64 / four-thread Cycles CPU 进程

## 结论

B52-D1 不能选择 adaptive production point，也不能给出有效的 `POINT_NOT_FOUND` 阴性结论。预注册的固定 128 spp 阳性控制没有复现 D5 的“128 spp parent”，所以实验按冻结规则判定：

`NATIVE_CPU_ADAPTIVE_QUALITY_COST_DERIVATION_INVALID`

这次失败发现了一个更上游的问题：D5/D6 所称的 128-spp CPU parent 继承了两个源 `.blend` 的 Cycles adaptive sampling，实际设置是 threshold≈`0.01`、min samples `0`、max samples `128`。D5 renderer 没有显式设置或报告这三个属性。B52 的真正 non-adaptive `FIXED_128` 因而不可能逐像素复现它。

## 直接证据

- 两个源场景经真实 Blender 5.2 零渲染读取，`use_adaptive_sampling=True`、threshold=`0.009999999776...`、min=`0`。
- D5 frozen renderer 中三个 adaptive 属性的赋值次数均为零，worker report 也没有记录它们。
- B52 `ADAPT_T010_M0` 在两个构图上都对 D5 parent 达到 7/7 production passes float32-exact。
- 真正 `FIXED_128` 只达到 TABLETOP 3/7、INTERIOR 2/7 exact；Combined、Normal、Vector 与活动 Cryptomatte 层发生改变，Depth 保持 exact。
- 30/30 进程、30/30 EXR 与 report 完成；12/12 同 profile 重复的八个 decoded parts 均 exact，三参考在两个构图均保持 3/3 distinct。

这证明不是随机不稳定、写盘损坏或进程复用，而是控制条件定义冲突。

## 描述性观察，不作 promotion

所有 adaptive 候选的 beauty 都通过三参考 3× floor，但没有一个满足完整联合门：

- `0.01/min32` 的 render saving 为 TABLETOP `14.67%`、INTERIOR `9.62%`，低于冻结的 20%；
- `0.01/min0` 相对真正 fixed control 仅节省 `9.60%/8.03%`；
- `0.001/min0` 两场景全部像素跑满 128，反而约慢 `0.66%/0.81%`；
- 所有能明显提前停止的 profile 都至少破坏了 D6 data semantic 或 exact Normal/Vector 门；
- 最严格的 profile 即使通过数据/辅助 pass，也没有提前停止或没有成本优势。

这些值来自无效实验，允许用于设计下一次预注册，不能作为生产选择。

## 失败与纠正链

第一版冻结 analyzer 在攻击 A16 对字典调用无参数 `pop()`，30 个 render 已完成但没有写 result。C1 只修正该攻击。C1 随后把“合法但未提前停止的候选”错误提升为“实验输入无效”；其 10/20 attack 结果被完整保留。C2 将 measurement validity 与 candidate gate 分开，最终稳定复现真正的上游控制失败。

独立审计对最终结果 byte-exact replay，30/30 artifacts、全部 frozen tool blobs、父输入与纠正链身份均匹配。审计仍为 `FAIL`，因为 base gate 真实失败、结果为 INVALID、仅 11/20 attacks 能在未修复基础失败的情况下到达目标 reason；这不是审计基础设施丢失证据。

## 对既有结论的修订

D5/D6 在共享的 inherited adaptive 配置内部仍然证明：把 max samples 从 128 降到 1–64 没有通过 exact 或 semantic data 门。但它们不能再被描述为“non-adaptive fixed 128 baseline”。production CPU 路线事实上已经在使用 Blender 默认的 `0.01/min0` adaptive sampling。

## 下一门

B52-D2 应把真正的 production baseline 明确冻结为 `adaptive=true, threshold=0.01, min=0, max=128`，使用新 seed 与 fresh processes，测试更宽松阈值能否在保持 beauty、decoded Depth/Cryptomatte 和任务相关辅助 pass 语义的同时获得至少 20% 成本改善。它不能复用 B52-D1 的候选结果作确认性结论。

机器证据：

- `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/results.json`
- `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/audit.json`
- `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/upstream-adaptive-control-diagnosis.json`
- `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/analysis.failure.json`
- `experiments/native-cpu-adaptive-quality-cost-derivation-v0-1/results.invalid-analysis-c1.json`
