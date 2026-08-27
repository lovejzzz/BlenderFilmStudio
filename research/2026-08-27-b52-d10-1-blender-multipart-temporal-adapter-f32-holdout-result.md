# B52-D10.1 · Blender multipart temporal adapter float32 holdout 结果

日期：2026-08-27

## 正式判定

`BLENDER_MULTIPART_TEMPORAL_ADAPTER_F32_HOLDOUT_SUPPORTED`

Base failure：`null`。独立 audit：`PASS`。

该判定晋级一个窄而明确的 production contract：在本机 Blender 5.2.0 LTS、opaque single-owner、orthographic、integer-motion 条件下，真实 multipart Combined/Depth/Vector/Object Index 可以被冻结 adapter 重复转换成 D9.1 的 canonical previous/current arrays，且 current-to-previous motion 为 `(-Vector.X,-Vector.Y)`。

D10 的 `BLENDER_MULTIPART_TEMPORAL_ADAPTER_HOLDOUT_NOT_SUPPORTED` 与 `FAIL` audit 不变。D10.1 是新 spec、新夹具、新工具和新 formal root，不是对 D10 的事后改判。

## 正式运行边界

一次且仅一次正式运行完成：

- 12 个独立 Blender source processes；
- 12 次 Cycles CPU ray renders；
- 6 个独立 adapter processes；
- 1 个 independent analyzer process；
- 共 19 个唯一 child PID；
- 0 source `.blend`；
- 0 external asset。

全部 37 个 base checks 为 true，37/37 mutation attacks 按预注册顺序返回指定失败原因。两次 source decoded Combined/Depth/Vector/Object Index 全部 exact；三 fixture 的七组 adapter arrays 在两次 repeat 中全部 exact。

## typed structural oracle

12/12 source cells 的 scene 与 layered Action structure 在明确的 IEEE-754 binary32 canonicalization 后 exact。每个 cell 同时满足：

- 跳过 binary32 round-trip 的 raw JSON-double scene 被拒绝；
- animated fixture 的 raw Action values 被拒绝；
- canonical ortho scale 向正无穷改变一个 float32 ULP 被拒绝；
- 一个 pass index 加一被拒绝。

Blender RNA 报告的 ortho scale 为 `18.100000381469727`，即 spec `18.1` 的 binary32 值。只有预注册列出的 RNA float paths 被 canonicalize；name、enum、integer、pass index、action topology、render/pass state、process count 与 artifact identity 仍 exact。这直接关闭 D10 的 verifier representation defect，而没有引入全局 epsilon。

## Vector 与 D9.1 motion

Object fixture 的两次 repeat 完全相同：

- expected XY `(-11,+7)`；p99/max `3.814697265625e-6 px`；
- expected ZW `(-18,+11)`；p99 `8.412853776644967e-6 px`，max `8.529922399520072e-6 px`；
- nearest wrong median `8.06225774829855 px`。

Camera fixture 的五个 visible owners、两次 repeat 全部通过。最坏值出现在 background：

- XY p99 `1.7059844799040144e-5 px`，max `3.0755072587198445e-5 px`；
- ZW p99 `1.7059844799040144e-5 px`，max `3.145679951185349e-5 px`；
- nearest wrong median 至少 `12.529960432791633 px`。

Static 两次 repeat 的 XY/ZW p99 都为 `1.52587890625e-5 px`，maximum 都为 `3.0517578125e-5 px`。这在冻结的非零容差内，并再次说明 exact-zero static gate 会错误拒绝真实 Blender output。

因此在已声明边界内，测量支持：

`Vector.XY = previous_screen_up - current_screen_up`

`Vector.ZW = current_screen_up - next_screen_up`

`D9.1 top-left current-to-previous motion = (-Vector.X,-Vector.Y)`

## Depth、ownership 与 raster orientation

五个预注册 depths 11.25、10.5、8.75、9.25、9.0 在 3 fixtures × 2 frames × 2 repeats 的 60 个 owner rows 全部通过，最大误差为 0。60/60 analytic 3×3 Object Index probes exact，每帧五个 ID 都可见；top marker centroid row 始终小于 bottom marker，vertical orientation 通过。

multipart roster 逐项为：

1. `BFS_F32_MASTER.Combined` RGBA；
2. `BFS_F32_MASTER.Depth` Z；
3. `BFS_F32_MASTER.Vector` XYZW；
4. `BFS_F32_MASTER.Object Index` X。

## 独立 audit 与身份

Audit 从正式 EXR 独立重建全部 adapter arrays，6/6 cells、42/42 arrays exact；12/12 source artifacts 与 12/12 PNG/sidecar diagnostics 通过。Frozen tools、parents、receipt/result self-hash、operation boundary 与 37 attack replay 全部通过。

- spec SHA-256：`11686c5e796c7bc1b4e45cf137c3d98347bc65bfec428f9d19545b55430f584b`
- freeze commit：`efd68ec1b1d2029c2526232290d8eadbe81972c7`
- preflight file SHA-256：`a2b9ad8f279d00d7f19a5dd3cda83b3434949084acb2f89e5228dc43fe32ad52`
- preflight self-hash：`a8293e5672aed374caab49b8aa31b6780e19ffa3b27cd6fa6a45fc5c177874d8`
- receipt file SHA-256：`703f0d37c7b5cda800a57a70221596ba68ceb61af99ae46664da378ae68b0128`
- receipt self-hash：`7399db873f6f7d7f6daa9eeb72b331d48494a8b43ae2ff0dcf102ba34fe9824d`
- result file SHA-256：`c0f94547b432159772029f67abe70da12ff0f236707d7f92896c75ee664ebc60`
- result self-hash：`acf9a3559b8d1a194e248930b58cff3050c12a94540cabff2b0989a6f2c8266f`
- audit file SHA-256：`f6ef6b2236aa8501ef533c88f5f1e9604f71b259d4beffc90825b14afdb52328`
- audit self-hash：`e582de3925486b39a317bb1e1614e2b32eef3c41e7aa70e1dbd84ee04eaf1188`

## 非主张与下一边界

D10.1 不支持 perspective、subpixel、deformation、transparency、multi-owner、Cryptomatte、hair、volumetric、DOF、motion blur 或跨版本/平台/GPU 等价，也没有把真实 beauty pixels 输入 D9.1 accumulator，更没有证明 temporal 画质或电影感。

下一步是 B52-D11：在任何新工具或输出前，预注册一个全新的 opaque textured integer-motion end-to-end holdout，将真实 Blender previous/current multipart renders → D10.1 adapter → D9.1 layer/depth temporal accumulator → D8 Raw float32 EXR bridge 串成一条可重放链。它必须同时验证 occlusion、disocclusion、out-of-bounds history、same-ID depth rejection、static control、clean repeats 与全链 operation/provenance identity。
