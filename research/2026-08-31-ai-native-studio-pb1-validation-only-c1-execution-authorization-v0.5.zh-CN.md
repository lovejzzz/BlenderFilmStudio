# PB.1 validation-only C1 attempt-02 执行授权 v0.5

Date: 2026-08-31

Gate: PB.1 Repository and source identity

Mode: validation-only / local-only source reuse / no engine source mutation / no engine remote write

Status: authorized; formal attempt-02 not yet executed at document creation

## 1. owner 精确授权

owner 在当前 Codex 任务中逐字授予：

> 我授权启动 PB.1 validation-only C1 attempt-02：不得再进行 public engine network clone；允许从 retained attempt-01 source=/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source 在 fresh attempt-02 root 中进行一次 local-only Git clone、创建一个 fresh local LFS storage 并只用一个 objects symlink 读取 retained immutable objects、进行一次 additional zero-network LFS materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b dependency local clone、一次 clean native arm64 build，以及最多两个 zero-render product identity/configuration starts；允许采用冻结的 attribute-context-independent F0 metric（14 textual paths=837 additions/64 deletions，加两个 exact former-LFS pointer object transitions），并允许提交推送 attempt-02 evidence。不得清理 attempt-01 的 3,918 个零字节 LFS tmp 文件，不得修改 film-engine source/commit/ref/tag，不得进行任何 engine remote write、LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

该文本与冻结的 v0.4 请求完全一致。授权只解除 attempt-02 的 C1 校正执行门，不扩张为
Phase B 源码开发权限。

## 2. 冻结绑定

- 授权请求：`specs/ai-native-studio-pb1-validation-only-c1-authorization-request.v0.4.json`
  / SHA-256 `b639ea9c9c02528abefb4268f16b27cb1a7cf17bad4cec592b47c55e8e62ab93`。
- 执行合约：`specs/ai-native-studio-pb1-validation-only-c1-execution.v0.5.json`。
- runner：`scripts/run-ai-native-studio-pb1-validation-only-c1.mjs`
  / SHA-256 `8b9489d625a5865f3e4304c01480dbcc966ab033e69a80054fe9ab87cf94ec9c`。
- independent auditor：`scripts/audit-ai-native-studio-pb1-validation-only-c1.mjs`
  / SHA-256 `58b1b3b0971d22a31d113de8a25384be3e8807e4d99a0f74739a54caede9ec7c`。
- tool-freeze research commit：`cd090927d139b40dda47b41b94063aa63f7956a8`。
- publication HEAD：`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`；F0 parent：
  `fa1b578bb421bbc82b3106b7d4223e11e65fae1d`。

## 3. 本次唯一允许的 formal 操作

1. 从 retained attempt-01 source 做一次 `--local --no-checkout` Git clone；public engine
   network clone 数必须为 0。
2. 在 fresh source `.git/lfs` 下建立新 storage，只允许其 `objects` 为指向 retained immutable
   objects subtree 的符号链接；checkout tmp 必须留在 attempt-02 root。
3. 只运行一次零网络 `git lfs checkout`，复算 6,669 个 tracked LFS paths、812,388,053
   bytes 与所有对象 SHA-256。
4. 用 14 个冻结 textual paths 的 `837 additions / 64 deletions`，加两个 former-LFS pointer
   object transitions，独立验证 F0 parent；不再使用受当前 attributes 影响的旧统计。
5. 从 retained clean dependency checkout 做一次本地 clone，固定到
   `a76ef917b4849ba2b1b1deb1a643e131a884a63b`。
6. 九项负控、历史、源码身份、license/generated-path、dependency 与资源门均 PASS 后，运行一次
   clean native arm64 build。
7. build PASS 后最多运行两个零渲染产品进程：`--version` 与隔离 HOME 的身份/配置审计。
8. 独立 auditor PASS 后，才允许提交并 push 本次 PB.1 evidence 到 BlenderFilmStudio 研究仓库。

## 4. 资源与停止规则

- formal mutation 前至少保留 `171,798,691,840` bytes free；不足时 fresh external root 必须保持 absent。
- attempt-02 external root 不超过 12 GiB，evidence root 不超过 32 MiB。
- build wall time 不超过 1,200 秒，peak RSS 不超过 4 GiB；同时只允许一个 native build。
- 任一 mismatch 写入新的 immutable FAIL/BLOCKED evidence 并立即停止，不在同一 root 修复或重试。
- retained attempt-01 的 3,918 个零字节 LFS tmp 文件必须原样保留。

## 5. 仍未授权

`film-engine` 的 source edit/new commit/ref/tag、任何 engine remote write、LFS upload/download、
release、签名、公证、DMG 创建或分发，以及 PB.2–PB.7 均未授权。PB.1 PASS 的 claim ceiling
仅为这台 admitted M2 Max 上的 repository/source identity 与一次 clean native arm64 build。
