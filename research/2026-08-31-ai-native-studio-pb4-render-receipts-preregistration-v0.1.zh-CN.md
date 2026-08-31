# PB.4 Preview, Final and Receipts 预注册 v0.1

状态：**在首次 PB.4 产品源码 mutation 前预注册**

PB.3 已证明 typed proposal、canonical BuildPlan、semantic scene、Film Workspace 和 Expert Mode 可以在同一次产品流程中无损往返。PB.4 不把历史 F0.5 输出重新命名为新结果，而是在真实 `film-engine` 产品中加入最小 Render Job surface 与 bounded render contract，再从 PB.3 accepted B01 `.blend` 产生全新的 EEVEE preview、Cycles multilayer EXR 和 receipts。

产品改动严格限制为三个 Python 路径：新增 `scripts/modules/film_studio_render.py`，扩展 `film_studio_workspace.py` 的 typed render-job 状态/操作，以及在 `space_topbar.py` 中显示 Render Job panel。不得改 C/C++，总新增不超过 600 行。产品必须先验证 self-hashed approved manifest、exact source、profile 和 evidence root；只能执行 PREVIEW/FINAL，不接受 proposal-originated Python、shell、network 或 arbitrary filesystem authority。

正式 profile 冻结为 B01 frame 1、640×360：EEVEE 16 samples RGBA PNG；Cycles CPU 32 samples、固定 seed、8 threads、无 denoise、ZIP half multilayer EXR，并要求 Combined / Depth / Normal。独立 auditor 不导入产品 render module，重新解码 pixels/passes，并交叉验证 process、cost、failure receipts。

三个负控均必须在 render call 前拒绝：篡改 manifest/approval、escaped output、缺失或不匹配的 PREVIEW receipt。最多一次 clean build、四次产品启动、两次真实 render call；work/evidence ceilings 为 2 GiB / 512 MiB。源码/build 使用 fresh PB.4 外部 roots，retained PB.1 与 PB.3 roots 完全不动。

Standing-autonomy charter 已授权这项有界本地产品开发、验证和普通 fast-forward 发布，不需要新的逐字授权。付费、force-push、release、binary distribution、签名、公证及 PB.5 仍不在本 gate。
