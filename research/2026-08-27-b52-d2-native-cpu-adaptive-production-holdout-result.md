# B52-D2：native CPU adaptive production holdout 结果

日期：2026-08-27

状态：`VALID NEGATIVE · NATIVE_CPU_ADAPTIVE_PRODUCTION_HOLDOUT_NOT_SUPPORTED`

正式运行：54 个 fresh Blender 5.2 LTS / native arm64 / four-thread Cycles CPU 进程

## 结论

B52-D2 没有找到能在两个冻结构图上同时满足完整 production payload 与成本门的更宽松 adaptive profile。最终判定是：

`NATIVE_CPU_ADAPTIVE_PRODUCTION_HOLDOUT_NOT_SUPPORTED`

这次是有效阴性，不是 D1 那种控制失效。显式 production baseline `adaptive=true / threshold=0.01 / min=0 / max=128` 的 6/6 新 seed cells 全部通过三参考 beauty、Sample Count、Cryptomatte 结构和三重复 exact 门。base failure 为 null，22/22 attacks 命中预期原因，独立 audit 为 PASS。

## 成本曲线确实存在

所有候选都降低了两个构图的 median mean effective samples。相对显式 production baseline，按两个构图中较差的 median render saving 计：

| profile | worst-variant render saving | 两构图成本门 | beauty cells | D6 data cells | exact aux cells |
| --- | ---: | --- | ---: | ---: | ---: |
| 0.015 / min0 | 11.62% | FAIL | 3/6 | 0/6 | 0/6 |
| 0.015 / min32 | 16.55% | FAIL | 3/6 | 0/6 | 0/6 |
| 0.02 / min0 | 17.92% | FAIL | 3/6 | 0/6 | 0/6 |
| 0.02 / min32 | 24.52% | PASS | 3/6 | 0/6 | 0/6 |
| 0.03 / min0 | 34.76% | PASS | 3/6 | 0/6 | 0/6 |
| 0.03 / min32 | 34.83% | PASS | 3/6 | 0/6 | 0/6 |
| 0.05 / min0 | 44.72% | PASS | 0/6 | 0/6 | 0/6 |
| 0.05 / min32 | 44.79% | PASS | 0/6 | 0/6 | 0/6 |

最高 savings 不是可免费领取的优化：它伴随可测量的 beauty 与 payload 变化。

## beauty 的构图依赖

TABLETOP 在 threshold 0.015、0.02 和 0.03 的全部重复都通过三参考 3× floor；0.03 的最接近边界项是 edge RMSE `2.9956×`。0.05 则在 linear 与 edge 上达到 `3.3200× / 3.4709×`，失败。

INTERIOR 更敏感。最温和的 0.015/min0 已达到 linear `3.2978×`、log-luminance `3.2993×`，因此失败；0.05 上升到约 `4.67×`。这说明单一全局 threshold 不能由当前两场景证据晋级。它不证明 scene-conditioned policy 不可行。

## 数据与辅助 pass 的边界

Depth 在 48/48 candidate cells 中通过 D6 gate；相对同 seed production baseline，foreground mismatch、stable-surface p99/max absolute error 和 p99 relative error都为零。

Cryptomatte 在 48/48 cells 中失败。最温和 0.015/min0 已出现：

- TABLETOP：7 个 hard-matte mismatch、worst matte max error `0.0375`；
- INTERIOR：15 个 confident dominant-ID mismatch、30 个 hard-matte mismatch、worst matte max error `0.0703125`。

更宽松阈值增加了错误；0.05 INTERIOR 达到 57 个 confident-ID mismatch 与 127 个 hard-matte mismatch。当前证据不能把这些错误称为视觉无关，因为尚未冻结具体 compositor 任务、边界局部化规则或合成输出容差。

Normal 与 Vector 在所有 48 个 candidate cells 都不是 float32-exact。D2 只记录 exact 失败，没有把 raw component 差异冒充任务失败；任务相关语义仍待单独派生。

## 可重复性与运行边界

- 54/54 fresh processes，54 个唯一 PID，零 timeout；
- 18/18 profile × variant 三重复在八个 decoded parts 上 exact；
- 两个三参考组均 3/3 distinct；
- 54 个 EXR 共 175,596,564 bytes；
- fresh-process wall 合计 180.542 s，render operator 合计 152.022 s；
- formal admission 在预计写入 384 MiB 后仍保留 107,958,173,696 bytes，超过冻结的 100 GiB reserve；
- analyzer base failure 为 null，22/22 attacks；
- independent audit 对 results byte-exact replay，7/7 frozen tools、全部 bound inputs 与 54/54 artifacts 匹配。

0.03 与 0.05 下，min0/min32 在两个构图的八个 decoded parts 均跨 profile exact。这是测量事实；一个合理推断是这些阈值下 Blender 的有效最小采样行为已经使显式 min32 不再改变结果，但 D2 没有检查 Cycles 内部停止控制流，不能把推断写成实现事实。

## 下一门

B52-D3 应先做零重渲染派生，使用保留的 54 个 EXR：

1. 把 Cryptomatte mismatch 定位到 object boundary / transition / stable interior，并量化真实 alpha-composite 输出误差；
2. 对 Normal 测量稳定表面的角度误差，对 Vector 按静态/运动语义与下游 temporal/compositor 用途分类；
3. 只派生任务语义和阈值，不追认 D2 candidate；
4. 另行预注册 INTERIOR 的 0.01–0.015 细粒度曲线与 scene-conditioned policy，使用新 seed/未见帧确认 beauty–cost 交点。

即使 D3 表明 payload 差异可接受，D2 仍保持阴性，因为 INTERIOR beauty 已阻止所有已测试候选。任何新 policy 都必须重新预注册和渲染。

## 非主张

- 不主张 adaptive sampling 无法降低成本；
- 不主张 exact Normal/Vector 是唯一合理生产语义；
- 不主张 Cryptomatte 的少量边界错误对所有合成任务都不可接受；
- 不主张 scene-conditioned threshold 不可行；
- 不外推到未见场景、2K/4K、动画、毛发、体积、透明、DOF、motion blur、GPU 或长序列热稳定性；
- 不主张人类电影感偏好。

机器证据：

- `experiments/native-cpu-adaptive-production-holdout-v0-1/run.receipt.json`
- `experiments/native-cpu-adaptive-production-holdout-v0-1/results.json`
- `experiments/native-cpu-adaptive-production-holdout-v0-1/audit.json`
