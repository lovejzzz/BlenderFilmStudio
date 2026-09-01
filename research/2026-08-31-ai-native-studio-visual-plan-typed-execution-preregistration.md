# PC4-VX1：让受限执行器消费视觉改进计划

状态：在任何新 `.blend` 派生、Blender start 或 render 之前冻结。

PC4-VU1 已证明软件可以把带截图证据的视觉判断编译成受限 plan；PC4-VX1 验证下一层：同一份 plan 是否能由通用 typed adapter 落地，而不是再次为当前作品手写物体修改清单。

执行器只看 plan 的 operation type、preset、target entities、shot IDs 和上限参数。镜头通过 packet/context 绑定；造型位置通过目标物体的 evaluated transform 与 bounding box 推导。当前物体名只作为 plan 已认证的实体引用，不能出现在几何算法的特例分支里。

本轮最多两次 Blender start、三张 640×360 PNG、一次 derivative save。第一进程消费全部六项 operation 并保存/渲染，第二进程 reopen 独立复核。光影状态必须保持，镜头只允许低于 plan 上限的 deterministic widening。三张图出来后必须直接视觉判断；机器 parts/polygons PASS 不能替代画面 PASS。

