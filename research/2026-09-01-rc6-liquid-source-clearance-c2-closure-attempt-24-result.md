# RC6 液体源间距 C2 closure attempt-24 结果

## 结论

`RC6-2026-09-01-source-clearance-c2-closure-attempt-24` 为 `PASS_CLOSURE / PASS_STATIC_CONTROL`。独立审计通过 `23/23`，选择 `clearance-35mm`，并解锁下一步“最终分辨率静态确认”。

本 closure 没有启动 Blender、没有重新烘焙、没有渲染，也没有修改 retained attempt-23。它逐文件重新绑定四组成功的 Blender 进程、四个测量结果、四个 baked-state `.blend`、每组精确 21 个第 1–7 帧 Mantaflow 缓存文件，以及 retained work/evidence 两个完整 manifest。

## 核心收据

- closure hash：`c85c8275b9d4d914caaf12bdfd955b1a54cec1e48d9822e1c78e96d2fe9e6004`
- independent audit hash：`1ebe21f68facfb1d4f176f7dd5ff23ca96840c8998ac410430d5ea8f06ae5e3c`
- independent audit：`23/23 PASS`
- selected cell：`clearance-35mm`
- requested clearance：`0.035 m`
- measured clearance：`0.0350000039 m`
- placement error：`3.9e-9 m`
- maximum source-volume error：`4.692535%`
- maximum temporal drift：`3.817851%`
- maximum outside-cup fraction：`0%`
- maximum non-manifold edges：`0`
- signed topology：每帧一个正体积外壳，最多一个完全嵌套负体积内壳

## 性能结论

同一 M2 Max 主机上，本轮每个真实七帧 Mantaflow 单元耗时 `86.78–113.77 s`。旧 48 帧 impact pipeline 耗时约 `11,296 s`，其中约 `11,197 s` 属于流体数据/网格阶段，渲染约 `38 s`。因此用户观察到“前 10 帧约 32 分钟”是旧 pipeline 的缓存范围与阶段编排问题，而非机器性能不足。

软件必须把以下策略固化为产品行为：

1. 先运行精确帧范围的短静态物理关卡；
2. 从实际缓存文件验证帧范围，不只相信 RNA/场景设置；
3. 分离 requested 与 measured placement，并在冻结的物理舍入误差内绑定；
4. 不通过就禁止进入长 impact bake；
5. 只有相同几何在最终分辨率静态确认后，才允许慢速 solver-owned tip。

## Claim ceiling

本结果只证明 resolution-96、七帧、静态容器中的局部液体初始几何通过冻结阈值。它不证明最终分辨率、倾倒、撞击、光影、镜头、渲染或成片质量。
