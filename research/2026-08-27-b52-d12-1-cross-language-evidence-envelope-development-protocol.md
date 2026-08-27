# B52-D12.1-DEV · 跨语言证据 envelope 开发协议

日期：2026-08-27  
状态：`PREREGISTERED_BEFORE_TOOLS`  
Blender processes：0

## 问题

D12 的 Python/Node 数组在 8/8 cells 中逐字节相同，但八份 Node report 的 self-hash 都被 Python 拒绝。差异不是数值，而是十进制 JSON 拼写：JavaScript 把约 `1e-5` 写成长小数，Python canonical dump 写成指数形式。

本开发实验检验一种更窄、更显式的证据 envelope：所有 JSON number 不再以语言选择的十进制字面量进入哈希，而是先转换为 `{"$f64be":"hhhhhhhhhhhhhhhh"}`。十六进制内容是 IEEE-754 binary64 的网络字节序；`+0/-0` 统一为正零；非有限数、超出 2^53−1 的整数值和不成对 surrogate 必须拒绝。

## 可证伪门

两个独立 CLI（Python 与 Node）必须对全部 16 份 retained D12 reconstructor report body 产生逐字节相同的 envelope 和 SHA-256。随后仅取 `measurements` 子树，八组对应 Python/Node cells 也必须逐字节相同。16 个攻击向量覆盖 signed zero、指数、safe integer 边界、非有限拒绝、key order、array order、escaping、Unicode 和保留键冲突。

若任意一个 report、measurement pair 或攻击向量不一致，结果必须是 `DEVELOPMENT_TYPED_EVIDENCE_ENVELOPE_NOT_COMPATIBLE`。通过标签也只表示当前算法与当前证据 corpus 兼容；它不能修改 D12 verdict，不能宣称 RFC 8785/JCS 合规，也不能直接进入生产 schema。

## 边界

输入只读；原 report、result、audit 和 diagnostics 不得改写。实验不启动 Blender，不使用模型或网络。工具路径与输出根目录在此协议提交前均不存在。

机器可读协议：`specs/blender-cross-language-evidence-envelope-development.v0.1.json`。
