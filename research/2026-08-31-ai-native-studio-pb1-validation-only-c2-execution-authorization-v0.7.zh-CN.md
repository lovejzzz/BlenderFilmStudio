# PB.1 validation-only C2 attempt-03 执行授权 v0.7

Date: 2026-08-31

Status: authorized, not yet executed

Gate: PB.1 Repository and source identity

## 1. 授权事实

Owner `lovejzzz` 在当前 Codex 任务中逐字提供了 C2 v0.6 请求所冻结的授权文本。该授权只解除 attempt-03 的执行门，不扩大 Phase B、发布、签名、公证、DMG 或 engine remote write 权限。

执行合约：`specs/ai-native-studio-pb1-validation-only-c2-execution.v0.7.json`。

冻结请求：`specs/ai-native-studio-pb1-validation-only-c2-authorization-request.v0.6.json`，SHA-256 `2c1747ef1b70c73b4fa3ec24b744c77afaa93d5b25e853602f22e99bbf77b3fb`。

冻结 runner：`scripts/run-ai-native-studio-pb1-validation-only-c2.mjs`，SHA-256 `b4169ab6e97b8caef412afedbd8cee9381db70ea95f319a9cd34aa3e2e9fdd50`。

冻结 independent auditor：`scripts/audit-ai-native-studio-pb1-validation-only-c2.mjs`，SHA-256 `c4b43343d59639cb8ddf4f0360cdddee2971cdce4ccfa0069b7d997c8d78c7b9`。

## 2. 精确授权文本

> 我授权启动 PB.1 validation-only C2 attempt-03：不得进行任何 public engine network clone；允许从 retained attempt-01 source=/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source 在 fresh attempt-03 root 中进行一次 local-only no-checkout Git clone，并在 checkout 4061e12bd45a2bec83e68d0cf49abbf56d4738f6 之前创建一个 fresh local LFS storage、仅以一个 objects symlink 读取 retained immutable objects；允许一次 additional zero-network LFS materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b dependency local clone、一次 clean native arm64 build，以及最多两个 zero-render product identity/configuration starts；允许继续采用冻结的 attribute-context-independent F0 metric（14 textual paths=837 additions/64 deletions，加两个 exact former-LFS pointer object transitions），并允许提交推送 attempt-03 evidence。不得删除、清理或修复 retained attempt-01/attempt-02（包括 attempt-01 的 3,918 个零字节 LFS tmp 文件与 attempt-02 的 6,424 个空 LFS hash directories），不得修改 film-engine source/commit/ref/tag，不得进行任何 engine remote write、LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

## 3. 执行边界

允许的有状态操作上限为：一次 retained-source local no-checkout clone、一次 checkout-before symlink 安装、一次零网络 LFS materialization、一次 exact dependency local clone、一次 clean native arm64 build、最多两次零渲染 product starts，以及 research evidence commit/push。

Attempt-01 与 attempt-02 必须保持原样。任何不匹配都在 fresh attempt-03 evidence 中记录 `FAIL` 或 `BLOCKED` 后停止；不得原地修复、重试、改变阈值或推进 PB.2–PB.7。
