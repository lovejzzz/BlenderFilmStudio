# B27 · 第 38 帧渲染历史隔离结果

日期：2026-08-26（America/New_York）  
预注册提交：`bda81f6`  
正式工具提交：`49250ce`  
冻结判定：`FAILURE_REPRODUCED_NO_SIGNIFICANT_HISTORY_ASSOCIATION`

## 主结果

24 个新 Blender 5.2 进程按冻结的交错次序运行。`HISTORY` 12 个进程各顺序渲染第 1–38 帧；`DIRECT` 12 个进程只渲染第 38 帧。共完成 468 次真实 render、468 个 PNG，24 个 PID 全部唯一。

固定参考是 B25-B 的第 38 帧。超过预冻结 B24 静态门的目标帧为：

- HISTORY：2/12 失败，10/12 exact；
- DIRECT：3/12 失败，9/12 exact；
- 双侧 Fisher exact：`p = 0.9999999999999999`；
- HISTORY − DIRECT 风险差：`−0.08333333333333334`。

因此不能支持“先渲染第 1–37 帧提高第 38 帧超门概率”。更强的反例是：DIRECT 在没有任何先前 render 调用时仍出现 3 次完全相同的超门模式。

## 两个稳定模式

24 个输出只出现两个 decoded RGB SHA：

- 参考模式 `c1363822…bf308`：HISTORY 10 次，DIRECT 9 次；
- 第二模式 `6e9685c1…0feaf`：HISTORY 2 次，DIRECT 3 次。

所有第二模式都相互 decoded-pixel exact；它们与 B25-A 第 38 帧也逐像素完全相同。两个模式只差同一位置的 17 个像素，边界框为 `x=267–272, y=112–117`，每个变化通道都是 +1 个 PNG8 code，alpha 不变。

这个空间/模式分析在主结果之后完成，状态固定为 `EXPLORATORY_POST_HOC_DOES_NOT_CHANGE_PREREGISTERED_DECISION`。它用于选择下一实验，不回写 B27 的主终点。

## 组内和跨组

- HISTORY 组内：46/66 exact，46/66 通过 ≤16 像素门；
- DIRECT 组内：39/66 exact，39/66 通过；
- HISTORY×DIRECT：96/144 exact，96/144 通过；
- 所有非 exact pair 都是同一组 17 像素、最大绝对误差约 1/255、RMS `0.000013060542585672345`。

这些 pair 并非独立样本，故不作为额外显著性检验；它们只验证二模态结构。

## 有效性与边界

23/23 个冻结攻击达到预期拒绝原因。实验绑定了 B27/B25/ReviewRenderSpec、Blender、OCIO、场景、plan、structure、configurator、renderer、comparator、runner、固定参考、进程次序、PID、帧序、输出哈希、布局、比较绑定、静态门和 Fisher 实现。

结果否证的是“连续帧历史是这个事件的充分解释”，不是所有 render-state 历史，也不定位 Metal、Eevee、TAA、rasterization 或 GPU 调度的内部原因。`p≈1` 不是两组严格等价的证明；固定 12+12 样本也没有等价性功效。

## 下一边界

下一项机器实验应固定 frame 38，在同一 Blender PID 内连续重复 render，并按两个预先已知 decoded RGB mode 分类。若单个 PID 内在两模式之间切换，则进程初始化不是充分边界，事件发生在 render invocation 或更低层；若每个 PID 内锁定、但 PID 之间不同，则初始化状态获得支持。B26 的独立观察者招募继续并行，不得由本实验代替。

主要产物：

- `experiments/frame-history-isolation-v0-1/results.json`
- `experiments/frame-history-isolation-v0-1/evidence/frame-0038.comparison.json`
- `experiments/frame-history-isolation-v0-1/variant-analysis.json`
- `research/2026-08-26-b27-frame-history-isolation-protocol.md`
