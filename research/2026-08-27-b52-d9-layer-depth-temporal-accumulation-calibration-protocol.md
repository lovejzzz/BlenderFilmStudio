# B52-D9 · Layer/depth-aware temporal accumulation calibration 协议

日期：2026-08-27

预正式工具修订：设计复核发现 CAMERA_PAN 的两层同速平移，只产生 out-of-bounds invalid history；而 naive control 本身仍执行 bounds rejection，因此该 fixture 不可能产生 ownership/depth ghost。任何正式工具或输出之前，naive sensitivity applicability 被明确限定为 FOREGROUND_CROSSING 与 DEPTH_SWAP_SAME_ID；wrong-sign motion 仍覆盖全部三组运动 fixture。阈值、坐标、fixture geometry、进程数与 verdict rule 均未改变，旧 spec hash 保留在 machine-readable amendment 中。

## 从 D8 到 D9

D8 已正式证明 external canonical float32 warp 可以经 Raw EXR、Blender 5.2 最小 compositor 与 RGBA32 EXR 逐位不变。但它没有回答历史帧中的颜色是否仍属于当前表面。D9 把问题收窄到 temporal correctness 的第一层：用 layer ownership 与 depth 判断历史是否有效，再做一个完全确定的两帧积累。

Blender 5.2 manual 将 Depth 定义为最近可见表面的相机距离，将 Vector 定义为基于前后帧的两组 screen-space 2D motion；data pass ownership 还受 alpha threshold 影响。AMD FSR2 把 depth clip 明确定义为 disocclusion mask，并要求调用方明确 motion-vector scale/range。Salvi 的 temporal supersampling工作同样把 reprojection 与 history validation 分开。D9 因而不把“有 Vector”误写成“历史可用”。

## 为什么先用 analytic integer motion

D9 不直接读取 Blender Vector。B52-D5 已说明 Blender Vector 负控存在可复现数值底噪，而 D7 又否证了通用 Blender Bilinear consumer。若同时引入 Blender Vector sign/component、subpixel filter 与遮挡，任何失败都会无法定位。

本实验只使用 integer screen-space motion，冻结 current→previous 坐标为 `q=(x−dx,y+dy)`，nearest lookup。它校准的是 ownership/depth validity 与 accumulation 本身。通过后，下一实验才可单独校准 Blender multipart Vector 到该 canonical convention 的 adapter。

## Ground truth construction

四个未见 analytic fixture 覆盖：

- 近景矩形跨过静态远景，产生 occlusion 与 disocclusion；
- 双层场景随相机二维平移，产生 out-of-bounds 历史；
- 两个表面故意共享 layer ID，但 depth 从 1 跳到 4，强迫 depth 独立拒绝；
- 零 motion 静态负控，全部 history 必须有效。

每个 fixture 直接从 layer trajectory 生成 current/previous RGBA、positive depth、float32 integer layer ID、motion、analytic validity mask 与 clean target。valid pixel 的 current/history 带等量反向 binary-exact noise，因此 0.5 平均必须逐 float32 等于 clean target；invalid pixel 的 current 本身就是 clean target。

历史只有在 q in-bounds、layer ID exact、depth 差不超过 `max(1,currentDepth)/1024` 且两侧 alpha>0 时有效。valid 输出是 float32 `0.5*current + 0.5*history(q)`；invalid 输出必须逐位等于 current。

## 双实现、敏感性与 Blender transport

Python scalar 与 Node JavaScript 各以独立进程实现四个 fixture，必须对全部输入、validity mask 与 resolved RGBA 完全一致。仅仅两实现相同仍不够：它们还必须分别 exact 命中直接生成的 analytic validity 与 clean target。

两个故意错误的 control 证明任务有信息量：

- unconditional history 忽略 ID/depth，在 FOREGROUND_CROSSING 与 DEPTH_SWAP_SAME_ID 各至少产生 32 个错误像素，最大误差至少 0.25；CAMERA_PAN 只测试 bounds 与 wrong-sign，不伪造不存在的 ownership mismatch；
- wrong-sign motion 使用 `q=(x+dx,y−dy)`，在有 motion 的 fixture 同样至少产生 32 个错误像素，最大误差至少 0.25。

每份 producer resolved RGBA 经独立 encoder 写成 Raw FLOAT EXR，再进入两个全新 Blender 5.2 D8-style passthrough 进程。正式矩阵是 4 Python + 4 Node + 8 encoder + 16 Blender = 32 个唯一 PID，16 次 compositor render，0 次 Cycles ray render。

## Exact gates 与边界

正式合同没有容差：validity mask、resolved pixels、encoder decode 与 Blender decode 都必须 exact；maximum resolved error=0、changed scalar=0。29 个 attacks 绑定父证据、预注册、工具、runtime、进程与 fixture roster、输入、ground truth、两个错误 control、encoder、Blender graph/output/repeat、diagnostics 与 self-hash。

通过只能写 `LAYER_DEPTH_TEMPORAL_ACCUMULATION_CALIBRATION_SUPPORTED`。它允许下一步预注册真实 Blender multipart adapter holdout，不允许宣称 Blender Vector 已校准或 production temporal 已解决。

D9 不覆盖 subpixel reprojection、半透明多归属、volumetric、motion blur、depth of field、arbitrary Cryptomatte coverage、temporal denoising、anti-aliasing、电影感或人类偏好。
