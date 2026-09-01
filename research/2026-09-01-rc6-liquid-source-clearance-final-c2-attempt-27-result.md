# RC6 最终分辨率静态确认 C2 attempt-27 结果

## 结论

`RC6-2026-09-01-source-clearance-final-c2-attempt-27` 的执行与独立审计为 `PASS`，科学结论为 `FAIL_FINAL_STATIC`，慢速倾倒保持锁定。

独立审计通过 `26/26`。缓存严格为 config/data/mesh 各第 1–7 帧，共 21 个文件；零渲染、零网络、零 engine write。先前两次包装器失败均在任何 bake 前停止，C2 普通 Python 组装预检成功到达最终变换后的场景编译边界后才启动 Blender。

## 收据

- receipt hash：`f9b4278e8d1727990db24431ead30517b31e28304e0d4ef2fa56b172b01ec057`
- independent audit hash：`9c05dd7b39dc18a98fe0601cdafc076bc8a4d8d847b797b21252b031bd4908fa`
- independent audit：`26/26 PASS`
- Blender process wall time：`1454.18785 s`
- scene-measured wall time：`1453.275196 s`
- work root：`31,935,896 bytes`
- final static verdict：`FAIL_FINAL_STATIC`
- slow tip unlocked：`false`

## 科学指标

- initial reconstructed volume：`0.0007199059 m³`
- final reconstructed volume：`0.0007107750 m³`
- frozen source volume：`0.0013283283766941 m³`
- maximum absolute source-volume error：`47.045556%`，FAIL
- maximum temporal drift：`2.291549%`，PASS
- maximum outside-cup fraction：`0.395315%`，PASS
- maximum non-manifold edges：`0`，PASS
- maximum connected components：`3`
- signed topology：FAIL；第 4–7 帧除嵌套外壳外出现一个固定的杯底以下正体积碎片

主液体外壳和嵌套负体积内壳在七帧内保持封闭，净体积随时间稳定。失败的主要矛盾不是 solver 漏液，而是 `mesh_particle_radius=4.5` 从 resolution-96 直接搬到 resolution-192 后不再代表同一个物理表面尺度。基础体素从约 `5.208 mm` 减半为约 `2.604 mm`，相同数值的 reconstruction radius 产生了约一半的净重建体积。

## 对“前 10 帧 32 分钟”的回答

同一机器上的 resolution-96 七帧单元耗时 `86.78–113.77 s`；本 resolution-192 七帧最终确认耗时约 `24.24 min`。M2 Max 在运行中约 11 核持续工作、无 swap，`pmset` 报告无 thermal/performance warning。

因此：

- 若是低分辨率验证层，10 帧 32 分钟说明 pipeline 失控；
- 若是 resolution-192 的最终 Mantaflow data+mesh 层，10 帧 32 分钟属于合理量级；
- 产品必须明确显示当前成本层、分辨率和阶段，并在低成本关卡通过前禁止昂贵层。

## 下一步

保留 attempt-27 的 immutable data cache。在 fresh roots 中复制完整缓存，只改变 mesh reconstruction radius，并从 data 重新生成 mesh；不得重新计算相同 data，也不得直接挂载 retained cache。候选应按 resolution/base-voxel 的物理尺度换算后冻结，并继续使用相同的源体积、时间漂移、signed topology、containment 和 manifold 阈值。
