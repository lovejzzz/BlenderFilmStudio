# B52-D12-C1 · Node 缺失父目录更正协议

日期：2026-08-27  
状态：`PREREGISTERED_BEFORE_CORRECTED_TOOL`  
类别：科学判定前的基础设施更正

## 为什么 D12 不能直接续跑

D12 已经创建正式根目录并完成 18 个有报告的子进程；第一个 Node 重建进程因输出父目录不存在而以 `ENOENT` 中止。此时没有完整进程矩阵、分析结果或审计，因此没有科学 verdict。续跑或覆盖原目录会混合两种工具状态，也会破坏一次性正式执行的证据边界。

失败根目录 `experiments/blender-projective-subpixel-reconstruction-holdout-v0-1/` 保持不可变。其 `run.failure.json` SHA-256 为 `ccb05339ec16b9d92350ad53552ae7368d2536e6e023bd0f1660ed9f7b67ec34`，保留提交为 `10537348e853603be1b83c5807945bbf6c1d9279`。

## 唯一获准的行为变化

原 Node 工具中的：

```js
fs.mkdirSync(args['output-dir'], { recursive: false });
```

在一个**新文件**中只改成：

```js
fs.mkdirSync(args['output-dir'], { recursive: true });
```

原工具不修改。新增契约测试必须在 cell 父目录和 `arrays/` 都不存在时调用更正后的 Node 工具，并要求成功输出，且与 Python 输出逐字节一致。

## 不允许因失败而改变的内容

科学规范 SHA-256 继续固定为 `dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2`。四个 fixture、47 mm 镜头、35 mm sensor、107×67 分辨率、对象/相机运动、投影公式、Vector 符号、双线性核、深度预测、有效性规则、所有质量阈值、57 个攻击和 verdict 规则均不得改变。

开发探针或无效执行中的局部数值不得用于调参。尤其不能因为第一个 Python cell 的误差很小而降低、提高或删除任何 gate。

## 从零重建的边界

C1 使用新根目录 `experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/`。必须重新运行：

- 16 个 Blender 5.2 Cycles source；
- 8 个 multipart adapter；
- 8 个 Python 和 8 个 Node reconstructor；
- 8 个 Raw EXR encoder；
- 16 个 Blender compositor bridge；
- 1 个独立 analyzer。

合计仍为 65 个成功且唯一的子 PID。所有测量输入必须由 C1 新根目录产生；禁止复制、链接或读取失败根目录中的 EXR、array、reconstruction 或 report 作为测量输入。

## 准入和失败规则

C1 工具冻结后，零正式输出 preflight 必须验证：

1. 原规范、原失败证据及原冻结工具身份；
2. Node 文件只有登记的单行语义差异；
3. 新增 missing-parent 测试与原 11 个 contract tests；
4. source/bridge 的真实 Blender 5.2 零渲染 API probe；
5. 新根目录不存在，且 64 MiB 预计写入后仍保留 100 GiB 空闲。

若 C1 在任何环节再次失败，保留新失败根目录并将它标记为另一项 invalid correction attempt；不得就地修补或恢复。只有完整矩阵和继承的独立审计都通过，C1 才能被视为基础设施有效；科学结论仍只能由未改变的 D12 analyzer/audit 给出。

机器可读协议：`specs/blender-projective-subpixel-reconstruction-node-parent-correction.v0.1.json`。
