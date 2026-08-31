# PB.1 validation-only C2 attempt-03 授权请求 v0.6

Date: 2026-08-31

Status: blocked awaiting exact owner authorization

Gate: PB.1 Repository and source identity

## 1. 为什么需要 attempt-03

Attempt-02 的正式 preflight 与 9/9 负控均通过，只消耗了一次本地 no-checkout
engine clone。随后 publication checkout 在 runner 建立 fresh `objects` symlink 之前，
创建了 6,424 个空 LFS hash directories。runner 按冻结停止规则拒绝覆盖该路径并停止。

独立 C1 failure audit 已 24/24 `PASS`：这些目录包含 0 个 object files、0 bytes、
0 symlinks；LFS checkout、dependency clone、native build、product start 与全部禁止操作均为 0。
Attempt-02 必须永久保留，不得原地修复或重试。

## 2. C2 唯一行为校正

C2 在 no-checkout local clone 后立即断言 `.git/lfs/objects` 不存在，创建指向 retained
immutable objects subtree 的唯一 symlink，然后才 checkout exact publication HEAD
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`。其余 metric、负控、资源阈值、依赖、
build、runtime identity、零远端写入和 claim ceiling 均不改变。

冻结工具：

- runner `scripts/run-ai-native-studio-pb1-validation-only-c2.mjs`
  / SHA-256 `b4169ab6e97b8caef412afedbd8cee9381db70ea95f319a9cd34aa3e2e9fdd50`
  / self-test 10/10 `PASS`；
- independent auditor `scripts/audit-ai-native-studio-pb1-validation-only-c2.mjs`
  / SHA-256 `c4b43343d59639cb8ddf4f0360cdddee2971cdce4ccfa0069b7d997c8d78c7b9`
  / self-test 6/6 `PASS`；
- machine request `specs/ai-native-studio-pb1-validation-only-c2-authorization-request.v0.6.json`
  / SHA-256 `2c1747ef1b70c73b4fa3ec24b744c77afaa93d5b25e853602f22e99bbf77b3fb`。

## 3. 请求的精确授权文本

若同意，请逐字回复：

> 我授权启动 PB.1 validation-only C2 attempt-03：不得进行任何 public engine network clone；允许从 retained attempt-01 source=/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.1-2026-08-30-mac-m2max-attempt-01/source 在 fresh attempt-03 root 中进行一次 local-only no-checkout Git clone，并在 checkout 4061e12bd45a2bec83e68d0cf49abbf56d4738f6 之前创建一个 fresh local LFS storage、仅以一个 objects symlink 读取 retained immutable objects；允许一次 additional zero-network LFS materialization、一次 exact a76ef917b4849ba2b1b1deb1a643e131a884a63b dependency local clone、一次 clean native arm64 build，以及最多两个 zero-render product identity/configuration starts；允许继续采用冻结的 attribute-context-independent F0 metric（14 textual paths=837 additions/64 deletions，加两个 exact former-LFS pointer object transitions），并允许提交推送 attempt-03 evidence。不得删除、清理或修复 retained attempt-01/attempt-02（包括 attempt-01 的 3,918 个零字节 LFS tmp 文件与 attempt-02 的 6,424 个空 LFS hash directories），不得修改 film-engine source/commit/ref/tag，不得进行任何 engine remote write、LFS upload/download、release、签名、公证、DMG 创建/分发，也不得启动 PB.2–PB.7。

## 4. 未授权状态

在收到上述精确文本前，attempt-03 external/evidence roots 必须保持不存在。工具自测不是
formal 授权。一般性的“继续”或长期目标不能代替这次新的 local clone、materialization、
dependency clone、build 和 product-start 授权。
