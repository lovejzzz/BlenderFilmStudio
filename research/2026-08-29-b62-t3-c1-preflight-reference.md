# B62-T3-C1：preflight 路径引用与 fresh retry root 修正

日期：2026-08-29

状态：PREREGISTERED — 修正前，v0.2 三棵 root 全部不存在

首次 T3 formal start 在写完 durable preflight 后、创建 job manifest 前退出。错误不是 Blender、Cycles、资源或 restart 失败，而是 runner 把 `writeExclusiveDurableHashed` 的返回值误当成含有 `path`；真实返回只有 `{record,file}`，因此 `repoUri(undefined)` 抛出 `ERR_INVALID_ARG_TYPE`。观测边界为 one Node start、zero Blender、zero render、job/formal roots absent，scientific verdict 为 null。

v0.1 preflight 与独立 failure receipt 永久保留。C1 只授权两项机械修正：从已知 preflight absolute path 构造 manifest URI；把 runner/auditor 的三棵 root 切换到 fresh v0.2。C1 correction 与本协议加入 freeze roster，v0.2 必须验证并绑定 v0.1 的 file/self hashes。

原 T3 的 288 帧、Cycles 64 spp、EXR/PNG、SIGTERM、真实 Codex host restart、receipt resume、24 gates、24 attacks、8 GiB ceiling、100 GiB reserve 与 HUMAN_PENDING 边界全部不变。
