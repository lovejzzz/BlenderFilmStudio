# B52-D9.1 · Textured layer/depth temporal accumulation fresh holdout 结果

日期：2026-08-27  
状态：正式完成并独立审计  
判定：`LAYER_DEPTH_TEMPORAL_ACCUMULATION_HOLDOUT_SUPPORTED`  
Audit：`PASS`

## 问题与边界

D9.1 问的是：在从未运行过、具有 surface-local 高对比纹理的两层整数运动序列上，两个独立实现能否精确重建 history validity，拒绝 ownership/depth discontinuity，识别错误 motion sign，并把 canonical resolved RGBA 通过真实 Blender 5.2 Raw EXR compositor 原样送出。

它不问、也不证明 Blender Vector 四分量的具体含义，不覆盖 subpixel filter、透明混合、体积、motion blur、depth of field、temporal denoising、抗锯齿、电影感或人类偏好。

## 正式设计

- 预注册 commit：`c14c3d430c2309fa50b6b7e12233de8cd82abc1b`
- 冻结工具 commit：`0f476ac`
- 四个 fresh fixtures：103×63 foreground crossing、107×61 camera pan、89×49 same-ID depth swap、71×43 static control
- canonical previous coordinate：`q=(x-dx,y+dy)`
- valid history：bounds、layer ID、depth tolerance 与 alpha 同时成立
- valid 输出：float32 `0.5*current + 0.5*previous(q)`；invalid 输出：current exact
- 正式进程：4 Python accumulator + 4 Node accumulator + 8 EXR encoder + 16 Blender 5.2 render = 32 个唯一子进程
- Cycles ray render：0

## 结果

| Fixture | Valid / total | Naive control | Wrong-sign control | Resolved → Blender |
|---|---:|---:|---:|---:|
| foreground crossing | 6,183 / 6,489 | 306 px / 1.015625 | 816 px / 1.125 | exact |
| camera pan | 5,700 / 6,527 | not applicable | 4,453 px / 1.125 | exact |
| same-ID depth swap | 3,632 / 4,361 | 729 px / 1.140625 | 270 px / 1.140625 | exact |
| static control | 3,053 / 3,053 | 0 / 0 | 0 / 0 | exact |

Python 与 Node 对十类 arrays 全部逐字节一致。独立 analyzer 重建的 current/history RGBA、depth、layer、motion、validity、resolved 与 clean target 全部一致。所有适用 sensitivity controls 均超过预注册的 ≥32 wrong pixels 与 ≥0.25 maximum absolute error；静态负控保持全 valid、零错误。

8 次 EXR encode/decode、16 次真实 Blender compositor render、8 组 repeat 和 4 组 producer-path convergence 全部 exact。全矩阵 maximum absolute resolved error 为 0，changed resolved scalars 为 0。30/30 attacks 通过。

## 独立审计

Audit 重新验证了冻结工具、五个 parents、四个 runtimes、所有 self-hash 与 operation counts；重放 8/8 producers、8/8 encoders，并逐字节重建 analyzer result 与 40/40 diagnostic artifacts。正式 run artifacts 为 32/32 exact，最终 audit 无 failures。

- run receipt SHA-256：`5086d4ba55c3bc5f80dea1c190e1c11f387bd09965fbc4e14bb2449ba7d982a6`
- result SHA-256：`a8e41983a5ec02df8977c44d76413b11cb0f63f2249941d5663875d30c28e7f1`
- audit file SHA-256：`6213aebcdb3364a60f2d256b0ba7c9ee66344b281a9e528f9b39feb594ebb83b`
- audit canonical self-hash：`b855009838e6726f7d8296951377200748b21d2e3e3866193f26c86f037383cf`

## 科学解释

支持的结论是：在本实验定义的整数、nearest、opaque、单 ownership/depth sample 模型内，外部 deterministic temporal accumulator 能精确拒绝 disoccluded/ownership-changed/depth-changed history，并能通过 Blender 5.2 Raw compositor bridge 保持 canonical float32 结果不变。

尚未解决的关键边界是输入语义，而不是输出 transport。下一实验必须重新预注册真实 Blender multipart adapter holdout，独立标定 Vector component order/sign、Depth 与 ownership 提取，再决定能否把 Blender production passes 接到 D9.1 accumulator。

## 机器可读证据

- `experiments/layer-depth-temporal-accumulation-holdout-v0-1/run.receipt.json`
- `experiments/layer-depth-temporal-accumulation-holdout-v0-1/results.json`
- `experiments/layer-depth-temporal-accumulation-holdout-v0-1/audit.json`
- `experiments/layer-depth-temporal-accumulation-holdout-v0-1/diagnostics/`
