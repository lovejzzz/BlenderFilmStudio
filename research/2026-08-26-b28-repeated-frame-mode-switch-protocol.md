# B28 · 同 PID 重复 frame 38 模式切换：预注册协议

日期：2026-08-26（America/New_York）  
状态：`PRE-REGISTERED · NOT EXECUTED`

## 从 B27 得到的问题

B27 否证了“连续渲染第 1–37 帧是 frame 38 异常的充分解释”。24 个新进程只产生两个 decoded RGB mode，而且两个 mode 在 HISTORY 与 DIRECT 都出现。下一条边界不是继续增加新鲜进程，而是观察一个已经初始化的 PID 在同一帧反复 render 时会不会自行切换 mode。

## 冻结设计

- 12 个新 Blender 进程，`P01`–`P12`；
- 每个进程只把 scene 设到 frame 38 一次；
- 不重载 `.blend`、不改 frame、不改 scene；
- 连续执行 12 次 `bpy.ops.render.render(write_still=True)`；
- 每次写出一个独立 PNG 并绑定 call ordinal、PID、文件 SHA；
- 总计 144 次 render、144 个输出、132 个 PID 内相邻 transition。

两个允许的 known mode 在任何 B28 输出前冻结：REFERENCE decoded RGB SHA `c1363822…bf308`，ALTERNATE SHA `6e9685c1…0feaf`。任何第三 SHA 不能被强行归类，而必须触发 `MODE_SPACE_EXPANDED`。

## 主终点和判定

主终点单位是 PID。若一个 PID 的 12 个输出同时包含 REFERENCE 与 ALTERNATE，它发生 known-mode switch。为避免把单个进程事件直接晋级为机制支持，至少两个独立 PID switch 才判 `WITHIN_PID_MODE_SWITCH_SUPPORT`。

判定顺序：

1. 任一 novel decoded RGB SHA：`MODE_SPACE_EXPANDED`；
2. ≥2 PID switch：`WITHIN_PID_MODE_SWITCH_SUPPORT`；
3. 恰好 1 PID switch：`SINGLE_PID_SWITCH_INCONCLUSIVE`；
4. 0 switch，且两个 mode 各锁定于 ≥2 PID：`PROCESS_LOCK_SUPPORT`；
5. 0 switch、两个 mode 都出现，但一方少于 2 PID：`BETWEEN_PID_SPLIT_INCONCLUSIVE`；
6. 只出现一个 mode：`MODE_NOT_REPRODUCED`；
7. 任一执行/证据门失败：`INVALID_EXPERIMENT`。

## 可证伪含义

如果同一 PID 在 REFERENCE/ALTERNATE 之间切换，process initialization 就不是充分边界，变化可在 render invocation 或更低层复发。如果每个 PID 内完全锁定、而不同 PID 落入不同 mode，初始化状态才得到支持。

结果仍不定位具体的 Eevee、Metal、TAA、rasterization 或 GPU 调度机制；也不代表人眼可见。B26 人类盲评继续保持独立 PENDING。

正式 renderer、classifier 和 runner 在本协议冻结时不存在；它们必须在下一提交实现并由结果绑定 SHA。23 个负例类别同时冻结。
