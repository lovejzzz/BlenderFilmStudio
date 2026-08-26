# B27 · 第 38 帧渲染历史隔离：预注册协议

日期：2026-08-26（America/New_York）  
状态：`PRE-REGISTERED · NOT EXECUTED`

## 为什么做这个实验

B25 的 429 个时间残差比较全部通过，但静态门只有 430/432：A-B 与 A-C 都在第 38 帧出现 17 个变化像素，刚好超过预先冻结的 16 像素上限；B-C 在同一帧 decoded-pixel exact。这个模式可能来自连续渲染历史，也可能只是进程级或每次 render 的微小变异。B27 只隔离一个变量：在渲染第 38 帧之前，是否已经顺序渲染第 1–37 帧。

## 冻结的两组

- `HISTORY`：12 个新 Blender 进程。每个进程严格按 1→38 顺序执行 38 次 `bpy.ops.render.render(write_still=True)`。
- `DIRECT`：12 个新 Blender 进程。每个进程直接设到第 38 帧，只执行一次 render；此前不得发生 render 调用。
- 共 24 个唯一 PID、468 次 render、468 个 PNG。执行次序在任何 B27 render 之前由固定种子冻结并交错，避免把时间漂移与 cell 混为一谈。

两组共用同一个 `.blend`、ReviewRenderSpec、OCIO、Eevee 控制、分辨率、采样数、线程数与输出接口。源 `.blend` 不允许被保存。

## 固定参考与主终点

参考图是 B25 的 B 组第 38 帧。选择规则不是看 B27 数据：B25 的 B 与 C decoded-pixel exact，预先按 replicate ID 字典序选 B。参考文件、容器 SHA 与 decoded RGB SHA 都写入 spec。

每个 B27 目标帧与该固定参考做一次比较。主终点是是否超过已经由 B24 holdout 支持、并在 B25 前冻结的三道 PNG8 静态门：

1. 最大绝对误差 ≤ 0.003922；
2. RMS ≤ 1/65536；
3. 变化像素 ≤ 16。

比较 `HISTORY` 失败数 / 12 与 `DIRECT` 失败数 / 12，唯一主检验是双侧 Fisher exact，α=0.05。不得中途停、追加样本或改阈值。

## 判定

- 有效且 p≤0.05，HISTORY 失败更多：`HISTORY_ASSOCIATION_SUPPORT`。
- 有效且 p≤0.05，DIRECT 失败更多：`OPPOSITE_DIRECTION_ASSOCIATION`。
- 两组都没有失败：`B25_ENVELOPE_FAILURE_NOT_REPRODUCED`。
- 至少一个失败但 p>0.05：`FAILURE_REPRODUCED_NO_SIGNIFICANT_HISTORY_ASSOCIATION`。
- 任一 provenance、身份、顺序、PID、输出、布局、绑定、统计或攻击门失败：`INVALID_EXPERIMENT`。

## 次要观察

报告 fixed-reference exact 数、逐次最大误差/RMS/变化像素、每组 decoded RGB variant 频率、组内 66 对和跨组 144 对比较。这些只用于定位，不得替代或重新定义主终点。

## 否证条件和边界

本实验可以否证“第 38 帧异常只在连续历史下出现”这一窄假设。非显著不等于两组等价；12+12 是固定的机制探测样本，不足以证明小效应不存在。即使出现显著差异，也只支持这台机器、这个 Blender build、场景、帧和渲染配置下的历史干预，不定位 Eevee 内部的具体根因。数值 exact 或过门不等于人眼不可见，更不等于电影质量结论。

正式 renderer、comparator 与 runner 在本协议冻结时尚不存在；它们必须在下一提交实现，并由最终结果绑定 SHA。
