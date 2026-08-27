# B52-D12-C2 · 负结果审计更正协议

日期：2026-08-27  
状态：`PREREGISTERED_BEFORE_CORRECTED_AUDIT_TOOL`  
范围：audit only；正式渲染 0；正式数据改写 0

## 已冻结的科学结果

C1 的 65-process 矩阵、receipt、result、diagnostics 和首次失败 audit 都保持不可变。冻结 result 为 `BLENDER_PROJECTIVE_SUBPIXEL_RECONSTRUCTION_HOLDOUT_NOT_SUPPORTED`，最早失败为 `DUAL_RECONSTRUCTION_IDENTITY`，47/57 attacks 为 true。

C2 不修复 Node report hash，不放宽 static exact threshold，也不改变任何科学证据。它只回答：这个负结果能否被独立 analyzer replay 和证据身份检查完整复现。

## 两个已定位的 audit-only 缺陷

首次 audit 用相对 formal root 启动，而正式 diagnostics sidecar 保存了绝对 URI。PNG bytes 相同，但 replay 生成的期望 sidecar URI 是相对字符串，因此在第一份 sidecar 终止。

用绝对 formal root 做的不保留诊断 replay 已经证明：analyzer verify 能退出 0，且所有证据 replay 相同；唯一剩余失败是 `attackTotality`。原 audit 把 totality 定义成 57/57 全为 true，这会自动拒绝任何合法的 negative result。正确的 totality 是：注册 roster/顺序完整、每个 `passed` 为布尔、true 的计数等于 `attacksPassed`、每项有审计方法；它不能把 false gate 改写成 true。

## C2 唯一允许的变化

新文件 `scripts/audit-b52-d12-projective-subpixel-holdout-c2.py` 必须以原 audit 为基础，只能：

1. 在构造路径前把 formal root 解析为绝对路径；
2. 在 replay 前绑定 C2 spec、preflight、receipt、result 和原失败 audit 的哈希；
3. 用 roster/order/type/count/method 一致性检查替代“所有 attack 均为 true”；
4. 在新的 `audit.c2.json` 中写入 correction provenance。

禁止重新运行 Blender、adapter、reconstructor、encoder 或 bridge；禁止写入或覆盖 receipt、result、diagnostics、原 audit 和原 audit tool。唯一允许的子进程是原 analyzer 的 `--diagnostics-mode verify` replay。

## 通过含义

C2 `PASS` 只表示冻结的负结果被独立、完整地重放和审计。它不会把 D12 改成 supported，也不会把 47/57 写成 57/57。若 C2 失败，必须保留其输出并另行预注册下一项 audit correction。

机器可读协议：`specs/blender-projective-subpixel-reconstruction-audit-c2.v0.1.json`。
