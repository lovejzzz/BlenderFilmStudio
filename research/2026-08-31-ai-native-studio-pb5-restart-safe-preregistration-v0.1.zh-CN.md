# PB.5 Restart-safe job control 预注册 v0.1

状态：**首次 PB.5 产品源码 mutation 前预注册**

PB.4 已证明真实产品可以从 accepted B01 workspace 产生 EEVEE preview、Cycles multilayer EXR 和可独立复核的 process/pixel/pass/cost/failure receipts。PB.5 不改变画面质量门槛，而是验证任务在受控中断后是否能只恢复未完成的 immutable stage。

正式顺序冻结为四次产品启动、两次 render call：第一次通过产品 `Resume Next Approved Stage` 执行 PREVIEW，在 artifact、stage receipt 与 resume-decision receipt 全部 fsync 后以 exit 75 模拟受控中断；第二次必须验证并跳过 PREVIEW，只执行 FINAL；第三次必须返回 COMPLETE 且零渲染；第四次合并三个负控和独立像素/pass审计，零渲染。

三个负控分别是：过期但self-valid的授权manifest、hash不匹配的伪造PREVIEW receipt、maximumRenderCalls=0的self-valid approved job。三者都必须在 `bpy.ops.render.render` 前拒绝。完成stage的artifact与receipt必须保持byte-exact，不能以“恢复”为名重新渲染。

产品源码仍只允许 `film_studio_render.py`、`film_studio_workspace.py`、`space_topbar.py` 三个Python路径，总新增不超过500行，不允许C/C++。Fresh external source/build/work和research evidence roots；最多一次clean build、四次product starts、两次render calls，work/evidence上限2 GiB / 512 MiB。

通用F0 preflight按60 GiB全量bootstrap假设在157 GiB free下显示BLOCKED；PB.5在任何build前使用更精确且更保守的12 GiB source/build/run projection。即时门槛是100 GiB reserve + 12 GiB projection = 112 GiB，当前约157 GiB满足。该差异必须写入evidence，不能把通用preflight误述为PASS。

Standing autonomy覆盖本次有界源码、构建、正式验证、证据提交与通过后的ordinary fast-forward。仍不允许force push、其他ref/tag、release、LFS upload、签名、公证、二进制分发或PB.6。
