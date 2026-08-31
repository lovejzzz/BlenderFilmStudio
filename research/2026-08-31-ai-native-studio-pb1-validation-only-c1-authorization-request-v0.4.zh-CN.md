# PB.1 validation-only C1 attempt-02 授权请求 v0.4

Date: 2026-08-31

Status: `BLOCKED_AWAITING_EXPLICIT_OWNER_AUTHORIZATION`

## 为什么需要新授权

attempt-01 已消耗原授权的一次 public no-smudge clone 和一次 local-only LFS
materialization。它在 dependency clone、native build 和 product start 之前因 attribute-context
统计口径失败而停止；没有 engine remote write。失败不能在同一 root 修补，原次数也不能默认重置。

## 仅有的两项 C1 修正

1. F0 parent identity 不再依赖当前 worktree attribute 分类：14 个 textual paths 的冻结统计为
   837 additions / 64 deletions，path-list SHA-256 为 `17f6289f…`；icon/splash 两个路径用
   merge-base→F0-parent 的 exact pointer Git blob OID、content SHA-256 和 bytes 分别验证。
   publication HEAD 的完整统计继续是 17 paths / 839 / 64 / 2 binary。没有阈值或 source object
   变化。
2. 不再把 fresh clone 的 `lfs.storage` 直接指向 retained storage。attempt-02 创建 fresh local
   storage，只让其 `objects` symlink 指向 retained immutable objects；`tmp` 留在 fresh root。
   retained storage 当前包含 6,488 个 exact objects / 810,236,112 bytes，以及 attempt-01
   留下的 3,918 个零字节 tmp files。attempt-02 前后整个 retained tree 必须不变；本请求不授权清理。

## 请求的精确权限

> 我授权启动 PB.1 validation-only C1 attempt-02：不得再进行 public engine network clone；允许从 retained attempt-01 source=/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source 在 fresh attempt-02 root 中进行一次 local-only Git clone、创建一个 fresh local LFS storage 并只用一个 objects symlink 读取 retained immutable objects、进行一次 additional zero-network LFS materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b dependency local clone、一次 clean native arm64 build，以及最多两个 zero-render product identity/configuration starts；允许采用冻结的 attribute-context-independent F0 metric（14 textual paths=837 additions/64 deletions，加两个 exact former-LFS pointer object transitions），并允许提交推送 attempt-02 evidence。不得清理 attempt-01 的 3,918 个零字节 LFS tmp 文件，不得修改 film-engine source/commit/ref/tag，不得进行任何 engine remote write、LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

没有逐字等价的新授权时，attempt-02 external/evidence roots 保持 absent，不创建 runner formal
receipt，不做 local clone/materialization/dependency/build/start。
