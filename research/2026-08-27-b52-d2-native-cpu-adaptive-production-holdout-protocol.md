# B52-D2：native CPU adaptive production holdout 预注册协议

日期：2026-08-27

状态：`PREREGISTERED · NO D2 RENDER OBSERVED`

## 为什么必须另起一次实验

B52-D1 不是一次有效的正/负候选选择。它把真正 non-adaptive 的 `FIXED_128` 当作 D5 parent 的阳性控制，但 D5 源场景实际继承了 Cycles adaptive sampling：`threshold≈0.01 / min=0 / max=128`。D1 的控制失败使整个候选结论无效，即便 30 个 render、重复确定性和大部分测量本身完整。

D2 不修补 D1 的结论。它把真实 production baseline 明文写入 spec，并用新的 seed 与全新的 Blender 进程做一次独立 holdout。

## 设计冻结

- production baseline：`adaptive=true, threshold=0.01, min=0, max=128`；
- 候选阈值：`0.015 / 0.02 / 0.03 / 0.05`，分别测试 `min=0` 与 `min=32`；
- 两个构图、每 profile 每构图三次 fresh process，共 54 个 Blender 5.2 CPU render；
- 所有 baseline/candidate 共享新的 `seedOffset=758759`，便于同 seed 对照；该 seed 未用于 D1；
- 复用 D1 的六个 immutable 512-spp reference EXR，只用于同一套三参考 beauty floor；
- 每个新 cell 仍输出 Combined、Depth、Normal、Vector、三层 Cryptomatte 与 Debug Sample Count。

阈值网格来自已公开的 D1 描述性观察，所以不是盲选。这个事实在 spec 中显式披露。D2 的确认性来自新的 seed、新的 candidate/control EXR 与新的 cost timing，而不是把 D1 数据重新命名。

## 判定顺序

1. 身份门：父证据、Blender、源 `.blend`、OCIO、六个 reference 与冻结工具必须匹配；
2. 容量门：预计写入 384 MiB 后仍至少保留 100 GiB；
3. baseline 门：显式 adaptive 设置正确、三重复八个 decoded parts exact、Sample Count 合法，并通过三参考 beauty floor；
4. 候选质量门：每次重复、每个构图均不超过三参考 3× floor；
5. 数据语义门：相对同 seed baseline，通过 D6 的 decoded Depth/Cryptomatte 阈值；
6. 辅助 payload 门：Normal 与 Vector 相对同 seed baseline float32-exact；
7. 机制门：候选在两个构图上的 median mean effective samples 都低于 baseline；
8. 成本门：候选在两个构图上的 median render-operator time 都至少降低 20%；
9. 选择门：只有完整通过前述联合条件的 profile 可被选择。

baseline 身份或有效性失败时，结果必须是 `INVALID`，不能把候选失败写成阴性结论。baseline 有效但没有候选通过时，结果才是 `NOT_SUPPORTED`。

## 为什么 fresh-process wall 不作为主成本门

fresh process 用于隔离 Blender 状态、验证 PID 与可重复性；其启动/加载成本不等于持久 worker 中多渲染一帧的边际成本。D2 仍记录完整进程 wall time，但生产选择的主成本指标冻结为 `renderSeconds`。后续长序列实验必须另行测量持续 worker、热状态和热稳定性。

## 辅助 pass 的保守边界

D2 继续要求 Normal/Vector exact，不是因为 exact 已被证明是唯一合理语义，而是因为当前还没有经过验证的下游任务容差。若候选只在这一门失败，结论只能是“不能在不改变现有 payload contract 的条件下推广”。下一步应单独派生 compositor/temporal 使用下的 Normal/Vector 任务语义，再以未见 seed/帧确认，不能在看到 D2 结果后临时放宽。

## 停止与保留规则

- output root 非空、身份不符或容量不够时，在零 render 处停止；
- 单 cell 超时或失败时停止后续矩阵，但保留已经产生的 stdout、stderr、report 与 EXR；
- analyzer/audit 缺陷只能用窄纠正协议修复，不允许修改已观察的阈值或选择规则；
- 无论正、负或 invalid，原始结果、攻击结果、工具哈希与非主张范围全部进入 repo；
- D2 不调用视频模型、云 GPU、Docker 或网络服务。

机器预注册：`specs/native-cpu-adaptive-production-holdout.v0.1.json`
