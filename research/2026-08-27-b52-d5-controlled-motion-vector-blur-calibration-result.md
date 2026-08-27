# B52-D5 · 受控运动 Vector Blur 任务校准结果

日期：2026-08-27

## 结论

正式结论是：

`CONTROLLED_VECTOR_BLUR_TASK_CALIBRATION_INVALID`

最早失败门为 `STATIC_NEGATIVE_CONTROL`。按照预注册规则，本分支停止把 Blender Vector Blur 作为 adaptive Vector 的裁判，不创建 fresh adaptive-Vector holdout。下一项实验应改用输入—输出关系可独立定义的 deterministic warp，或另一个与 Blender Vector Blur 无关的 optical-flow task。

这不是“Vector Blur 节点失效”的结论。两个受控运动 fixture 都产生了强、可复现且随 shutter 严格递增的响应。失败的含义更窄：当前冻结的任务合同不能同时把真实运动与 Cycles 静态 Vector pass 的数值底噪可靠分开，因此它没有资格承担后续候选选择。

## 正式运行边界

- 运行时：Blender 5.2.0 LTS，build `fbe6228777e7`，Darwin；
- 6 个 fresh Cycles CPU source 进程：3 fixture × 2 repeats；
- 24 个 fresh CPU compositor 进程：3 fixture × 4 shutters × 2 repeats；
- 30/30 PID 唯一，30/30 render call 完成；
- 24/24 multipart source pass pairs decoded exact；
- 12/12 compositor output pairs decoded exact；
- 9 张固定尺度 PNG 与 9 个 canonical sidecar；
- 20/20 独立合约攻击命中预期失败原因；
- 进程累计 wall time 58.235777 s，其中六次 Cycles render 累计 2.348394 s；
- source EXR 共 11,529,878 bytes，compositor EXR 共 41,212,400 bytes。

EXR 容器哈希在重复间不同，但所有预注册 decoded-array repeat gate 均逐位完全一致。这与 D4 的容器时间元数据观察一致，不能用容器字节差异替代像素复现性判断。

## 两个运动 fixture

### OBJECT_OCCLUSION_X

前景平面在 frame 0/1/2 的 x 为 −1/0/+1，并穿越静态遮挡平面。

- Vector maximum：51.200012 px；
- Vector p99：51.200008 px；
- 超过 1 px：5,895 pixels；
- shutter 0：RGB maximum `2.38419e−7`，0 pixels 超过 `1/65536`；
- shutter 0.25/0.5/1.0 RMSE：0.042265 / 0.060391 / 0.086485；
- 对应 p99：0.123155 / 0.281903 / 0.567524；
- shutter 1 / 0.25 RMSE ratio：2.046244。

Vector、shutter-zero、shutter-half 与三项 dose-response 门全部通过。

### CAMERA_PAN_X

正交相机在 frame 0/1/2 的 x 为 −0.5/0/+0.5，几何保持静止。

- Vector maximum：25.600033 px；
- Vector p99：25.600021 px；
- 超过 1 px：147,456 pixels；
- shutter 0：RGB maximum `2.38419e−7`，0 pixels 超过 `1/65536`；
- shutter 0.25/0.5/1.0 RMSE：0.035245 / 0.051398 / 0.074459；
- 对应 p99：0.111860 / 0.204187 / 0.457536；
- shutter 1 / 0.25 RMSE ratio：2.112576。

该 fixture 同样通过全部运动与 dose-response 门。

## 静态负控为什么失败

`STATIC_CONTROL` 没有任何 keyframe。它的 Vector maximum 为 `2.67029e−5` px，低于 frozen maximum gate `1/1024`；但 p99 为 `1.90735e−5` px，高于 frozen p99 gate `1/65536 = 1.52588e−5`。共有 3,695 pixels 越过该 p99 使用的数值尺度。

与此同时，shutter 0/0.25/0.5/1.0 的 compositor 输出全部保持相同的极低差异：RGB maximum `2.38419e−7`，没有像素超过 `1/65536`。因此观察到的是可复现的静态 Vector 数值底噪，不是可见 blur 泄漏。

如果在看到结果后把 p99 门放宽，这个校准会“通过”，但那会破坏预注册的拒绝条件。D5 的用途正是判断这份 oracle 合同是否事先有效，而不是为节点寻找一个事后可通过的阈值。

## 独立审计

审计状态为 `PASS`，科学结论仍为 `INVALID`。两者回答不同问题：

- scientific verdict：冻结的任务是否通过；
- audit status：失败证据是否完整、可重放、未被替换。

独立 analyzer replay 与原始 `results.json` byte-exact；6/6 source EXR、24/24 compositor EXR、30/30 report、18/18 diagnostics、6/6 frozen tools、所有父证据与 source post-observation 均匹配。结果 SHA-256 为 `b436f8c9905ff08c322bef3d7a9fa950bf7934b3f7d93ae25fcbabdc5b06862e`；审计 SHA-256 为 `fb2b2246c24696e6aef52dbb18c83fe4d69e21353aba457d948279322cc3feb5`。

## 非主张

- D5 没有评价任何 adaptive profile；
- D5 不证明 Vector Blur 的视觉质量、遮挡正确性或电影感；
- 静态底噪不证明 Blender 有 bug；
- 两个 moving fixture 通过，不足以绕过 static negative control；
- 该结果不能修改 D2、D3 或 D4；
- 没有视频生成模型、外部资产或人工主观评分参与。

## 下一步

选择 deterministic warp，而不是继续调 Vector Blur 阈值。新任务应直接消费冻结的 Combined、Depth 与显式位移场，以一个独立、数学定义清楚的 CPU reference sampler 生成目标；Blender 只负责提供和消费数据，不再同时充当被测数据源与裁判。新实验必须重新预注册边界条件、遮挡规则、采样核、坐标方向、repeat gate 和 fresh holdout，且不能回头推广 D2 的任何候选。

Artifacts: `experiments/controlled-motion-vector-blur-calibration-v0-1/`, `specs/controlled-motion-vector-blur-calibration.v0.1.json`, `experiments/controlled-motion-vector-blur-calibration-preflight-v0-1/frozen-tool-preflight.json`.
