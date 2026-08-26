# B28 · 同 PID 重复 frame 38 模式切换结果

日期：2026-08-26（America/New_York）  
预注册提交：`a6a9870`  
正式工具提交：`0b905a1`  
冻结判定：`WITHIN_PID_MODE_SWITCH_SUPPORT`

## 主结果

12 个全新 Blender 5.2 进程各自只设置一次 frame 38，随后在不改变 frame、scene 或 `.blend` 的条件下连续调用 `bpy.ops.render.render(write_still=True)` 12 次。共完成 144 次真实 render、144 个 PNG，12 个 PID 全部唯一。

- 12/12 个 PID 同时出现冻结的 `REFERENCE` 与 `ALTERNATE` decoded RGB mode；
- `REFERENCE` 116/144，`ALTERNATE` 28/144；
- 132 个相邻调用中发生 42 次 mode transition；
- `REFERENCE→ALTERNATE` 22 次，`ALTERNATE→REFERENCE` 20 次；
- 未出现第三个 decoded RGB SHA；
- 23/23 个冻结攻击达到预期拒绝原因。

冻结支持阈值是至少两个独立 PID 发生 known-mode switch；观察值为 12 个。因此主判定为 `WITHIN_PID_MODE_SWITCH_SUPPORT`。

## 这个结果排除了什么

B27 已表明连续渲染 frame 1–37 不是 frame 38 第二模式的充分解释。B28 进一步表明，一个 Blender 进程也不会在初始化时永久锁定某个 mode：同一 PID、同一 frame、同一 scene，在相邻 render invocation 之间可双向切换。

因此，“进程初始化状态决定这次输出模式”也不是充分解释。可复现边界被缩小到每次 render invocation 或更低层的 Eevee / Metal / rasterization / temporal sampling / GPU execution 工作，但本实验不能在这些内部机制之间做归因。

## 序号描述

12 个调用序号的 `ALTERNATE` 计数依次为 `2, 1, 0, 1, 4, 2, 2, 2, 5, 3, 2, 4`。这是预注册次终点的描述性输出；B28 没有为 ordinal effect 冻结统计模型，因此不据此宣称随调用次数上升、周期性或热状态效应。

每个 PID 至少出现一次 `ALTERNATE`，次数范围 1–4。所有 42 次转换都只发生在两个冻结 mode 之间，且转换方向接近平衡。没有把同一 PID 内的 132 个相邻 pair 当作 132 个独立过程样本。

## 有效性与边界

实验固定并验证了 B28、B27 result、B27 variant analysis、ReviewRenderSpec、Blender binary、OCIO、scene、plan、structure、configurator、renderer、classifier、runner、两个 anchor、进程次序、PID、frame-set 次数、render-call 次序、PNG layout、文件哈希、classification binding、mode/sample/threshold/decision contract 与 human-review PENDING。

结果只证明该 scene、frame、Blender build、Apple M4 Max / Metal 后端与固定 Eevee profile 下的 decoded RGB 双模式可以在 render invocation 之间复现。它不证明具体 race、驱动缺陷、所有 Eevee 镜头都会发生、差异肉眼可见或成片质量不合格。PNG8 不是 EXR master；B26 人类观察者门仍然独立且 `PENDING`。

## 下一边界

下一项机器实验应把 render invocation 拆成更细的可干预边界，例如固定进程内切换 TAA reprojection、Fast GI 或 rendering context 的复位/重建条件，并观察两个 mode 的频率是否改变。任何机制假设必须先冻结处理、样本数与判定；B28 的 28/144 只能用于设计，不可同时用于确认同一效应。

主要产物：

- `experiments/repeated-frame-mode-switch-v0-1/results.json`
- `experiments/repeated-frame-mode-switch-v0-1/evidence/mode-classification.json`
- `experiments/repeated-frame-mode-switch-v0-1/evidence/classification-binding.json`
- `research/2026-08-26-b28-repeated-frame-mode-switch-protocol.md`
