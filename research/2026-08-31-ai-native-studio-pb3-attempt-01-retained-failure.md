# PB.3 validation-only C2 attempt-01 retained failure

日期：2026-08-31
状态：`FAIL — PRE-BLENDER HARNESS INPUT HASH`
Blender start / proposal execution / BuildPlan write / render：`0 / 0 / 0 / 0`

## 结果

用户逐字批准 PB.3 validation-only C2 attempt-01 后，execution contract 作为唯一变更路径提交并公开为 `ee68a977a018a1e94c4161674f5173d23a85f93e`。Admission 通过：约 174.4 GB 可用空间，research/source worktrees clean，binary 与两个 public HEAD exact，attempt-01 roots fresh。缺少 `--execute` 的负控在创建 roots 前正确拒绝。

正式 runner 创建 work/evidence 两个 root 后，在 B01 fixture 复制第一个 common input 前按停止规则终止：

- path：`specs/scene-spec.v0.1.schema.json`
- v0.2 tool contract expected SHA-256：`b308c7832d4f4b02e16f930f19dcf1baae7475d2f283aee3cb453f05a2224a`
- actual SHA-256：`b308c7832d4f4b02e16f930f19dcf1baaeae7475d2f283aee3cb453f05a2224a`
- bytes：`10,516`

这是 SHA 中 `...f1baae747...` 与 `...f1baaeae747...` 的单字符抄录错误。文件从最后一次路径修改提交 `a4d376d6…` 到 C1/C2 freeze、authorization parent 和 execution commit 始终保持 actual hash；不是 source 变化。

## 完整输入盘点

独立盘点 v0.2 的 4 个 common inputs 与 B01/B02 9 个 fixture inputs，共 13 个路径：12 个 exact，唯一 mismatch 即上述 SceneSpec schema。没有第二个隐藏输入哈希问题。

## 停止状态

- work root：已创建，0 regular files，0 symlinks；
- evidence root：已创建，runner 停止时 0 files；随后只写入 immutable `failure.json` 与 `audit-failure.json`；
- input copies：0；
- Blender starts：0；
- proposal executions / BuildPlan writes / scene builds / saves / reopens：全 0；
- renders / network calls / engine source edits / engine remote writes：全 0；
- engine source 仍 clean `4061e12bd45a2bec83e68d0cf49abbf56d4738f6`。

Attempt-01 roots 永久保留，不删除、不修复、不原地重试。

## Evidence

- execution contract：`specs/ai-native-studio-pb3-validation-only-execution-c2.v0.6.json`
  - file SHA-256：`69577f02afdd47c857617477d747682fd86421d65f56a6c49753054af34db41d`
- failure receipt：`experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-01/failure.json`
  - file SHA-256：`b584261e6782b093698f274ea235e0e8c173ccdcff3d2989b22e999edb000791`
  - self hash：`ebf23c3aaac9bfebc9fff32909fe2b984a875ee4289abdc20968cbba860095c3`
- independent failure audit：`experiments/ai-native-studio-phase-b/PB.3-2026-08-31-mac-m2max-attempt-01/audit-failure.json`
  - verdict：`PASS 24/24`
  - file SHA-256：`a9d064bf3ab8626444a0140fe20ecb34b0a618b01f139c0bc05f3d5e79d3ef3d`
  - self hash：`cf930924c2215f30c871fc58d08363a9f83ae0537097ef3ec03e548b86d93926`
- C3 correction：`specs/ai-native-studio-pb3-validation-c3-input-hash-correction.v0.7.json`
  - file SHA-256：`701e40769ad731d5d2ec2724aded1776b81268be2a13f6d798982afa2abaf634`

## 下一步边界

C3 只允许未来 versioned tools 把 `commonInputs[0].sha256` 从错误值改为已独立证明的 actual value；source/fixture bytes、oracle、thresholds 与权限均不得改变。Attempt-01 的一次性授权已经消耗。Fresh attempt-02 需要新的 exact execution contract 和明确授权；PB.4–PB.7 继续未授权。
