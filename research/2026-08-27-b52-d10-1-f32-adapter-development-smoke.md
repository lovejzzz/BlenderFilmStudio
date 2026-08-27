# B52-D10.1 · float32 adapter pre-freeze development smoke

日期：2026-08-27

分类：`DEVELOPMENT_ONLY_NOT_FORMAL_NOT_PROMOTABLE`

## 目的

在冻结 D10.1 工具前，只检查新 typed structural oracle 是否真正对应 Blender 5.2 RNA 读回语义，以及新命名的 multipart pass 和 adapter 路径能否运行。该 smoke 使用已经预注册的一组 fixture，因此其任何数值都不能满足正式 holdout gate。

## 实际运行

六个彼此独立的 Blender 5.2.0 LTS process 从 factory state 渲染三个预注册 fixture 的 frame 0 与 frame 1，各调用一次 Cycles CPU。三个独立 Python process 分别读取对应 multipart EXR 并写出七组 D9.1 canonical arrays。九个 PID 均不同；正式 root 始终不存在。

Blender 报告的 ortho scale 为 `18.100000381469727`，等于 spec `18.1` 的 IEEE-754 binary32 round-trip。六帧 canonical scene 与 Action structure 都 exact；故意跳过 round-trip 时 applicable structure 不相等。一个 ULP 的 ortho-scale mutation 与 pass-index +1 mutation 在 6/6 source cells 都被 exact comparison 拒绝。

multipart roster 与通道为 Combined RGBA、Depth Z、Vector XYZW、Object Index X，均使用新 view layer `BFS_F32_MASTER`。三 fixture 的 15 个 owner rows 都可见，15 个 analytic 3×3 probes exact，Depth maximum error 均为 0。

Object mover 的 XY p99/max 为 `3.814697265625e-6 px`；ZW p99/max 为 `8.412853776644967e-6` / `8.529922399520072e-6 px`，nearest wrong median 为 `8.06225774829855 px`。Camera 的最坏 XY/ZW maximum 是 `3.0755072587198445e-5` / `3.145679951185349e-5 px`，nearest wrong median 至少 `12.529960432791633 px`。Static XY/ZW p99 为 `1.52587890625e-5`、maximum 为 `3.0517578125e-5 px`。三个 adapter report 与六个 source report self-hash 均有效。

## 解释边界

该结果说明候选实现没有重现 D10 的 JSON-double/RNA-float32 verifier defect，并且 object、camera、static 三条真实 Blender source→adapter 开发路径可以运行。它没有测试第二次 clean repeat、完整 19-process roster、37 attacks、正式 freshness/preflight 或 audit，因此不能晋级 production contract。

Observation internal hash：`31627cf6eb892d2f3f0fef1e749b81a53f7c34bfdae1ebe4692f99dbe11de682`。
