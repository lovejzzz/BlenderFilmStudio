# BlenderFilmStudio 稳定性优先目标 v0.1

Date: 2026-08-28
Status: ACTIVE EXECUTION CHARTER
Priority: Gate 0 blocks Gate 1 and Gate 2

## 重新定义后的目标

把 BlenderFilmStudio 建成一个**稳定、可恢复、可审计的 Blender 5.2 电影生产系统**。当前首要任务不再是继续扩张功能，而是先消除会让 Codex 宿主、工作进程或证据链中断的系统性风险。只有稳定性门通过，才恢复正式工作流和电影质量实验。

## 当前触发证据

2026-08-28 的 Codex 桌面端崩溃报告显示：

- process: `ChatGPT` / identifier: `com.openai.codex`
- version: `26.820.80927 (7271)`
- exception: `EXC_BREAKPOINT (SIGTRAP)`
- triggered thread: `Chrome_IOThread`
- main thread同时位于 `v8::ValueSerializer::WriteValue`

这份报告支持把调查方向收敛到 Codex 内嵌 Chromium 的 I/O、跨进程消息或值序列化路径，但**尚不足以证明唯一根因**。在得到可重复证据之前，不把 Blender、磁盘或某一个网页标签武断认定为根因。

## Gate 0：Codex 宿主稳定性

Gate 0 必须先完成：

1. 保存崩溃报告、应用版本、系统版本、时间线和当时资源状态。
2. 建立有界复现实验矩阵，分别隔离浏览器标签数量、页面复杂度、工具输出体积、状态更新频率、内存、磁盘和并发子进程。
3. 建立默认防护：最少浏览器标签、禁止把超大原始输出直接送入 UI、工具输出截断/落盘、低频进度更新、严格磁盘余量、精确 PID 回收、断点续作。
4. 每次实验先声明资源预算、停止条件和恢复路径；出现 UI 卡死、SIGTRAP、磁盘越线、孤儿进程或证据链断裂立即停止重型实验。
5. 通过一组预登记、连续、受控的稳定性验收；通过前禁止长时渲染和高并发 Blender 任务。

## Gate 1：工作流正确性

在 Gate 0 通过后，将 `SceneSpec → immutable BuildPlan → admission-gated native Blender 5.2 compiler` 固化为唯一正式入口，并用真实 Blender 验证：

- 确定性与结构哈希；
- 人物、场景、镜头、光影和输出一致性；
- 资源收据与磁盘准入；
- 故障注入、幂等恢复和重复进程抑制；
- 独立审计与不可变证据链。

## Gate 2：电影质量与成本

在 Gate 1 通过后，用代表性真实镜头测量：

- 画面真实感和电影感；
- 时序一致性与镜头连续性；
- 渲染质量、吞吐、峰值资源和失败成本；
- 每秒、每镜头和每分钟成片的边际成本。

最终交付是可重复的端到端成片流程，而不是单张漂亮样片。

## 永久实验规则

- 先注册协议，再运行实验。
- 先检查磁盘、内存、进程和恢复点，再启动 Blender。
- 原始大证据写入文件，只向 Codex UI返回摘要和路径。
- 浏览器只保留当前验证所需的最少标签，完成即关闭。
- 所有算法代码、实验收据、失败反例和 journal 都提交并推送；失败证据不得因“不好看”而删除。
- 不通过降低安全门槛来换取一次成功。

## 当前停止线

在 Gate 0 的防崩规程和最小稳定性验收就位前，B58 official formal run 暂缓。允许继续的工作仅限低风险静态检查、证据整理、轻量实现和稳定性诊断。
