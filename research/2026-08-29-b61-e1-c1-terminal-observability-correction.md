# B61-E1-C1：Blender Python 失败码、原始日志与阶段 ledger 修正

日期：2026-08-29

状态：v0.2 工具修改与执行前预注册

## v0.1 正式反例

B61 v0.1 完成 preflight admission 后，只启动了 WIDE-A。真实 Blender 在冻结 OCIO 下写出 `frame-0001.exr`，随后没有 pixel report、PNG 或 run report。Supervisor 观察到 exit 0，但 invocation 没有 `--python-exit-code 1`；stdout/stderr 只保留了字节数和 SHA，未保留正文。因此现有证据只能证明“Python 路径在第一份 EXR 后未完成”，不能证明异常发生在 EXR reopen、pixel extraction、PNG save 或 report write。

v0.1 attempt tree 固定为 4 files / 3,102 bytes / `f6a21fb52adb213f046ffbab0d70b2fbad9b2a27b0e9b23b54176058449cd6b3`；formal tree 固定为 4 files / 1,348,155 bytes / `bf4829188e4a5e5933af245bc2a3f2acb101b595a34cbb4e5bb4939153aa3c53`。两根及 preflight v0.1 均不得修改、删除、覆盖或复用。

## 唯一授权修正

1. 每个 render Blender invocation 在 `--python` 前加入 `--python-exit-code 1`。
2. Supervisor 最多捕获 stdout/stderr 各 4 MiB；在写 process receipt 前，先用 exclusive + fsync 持久化原始日志及其完整流 byte count/SHA/truncation 状态。
3. Render Python 使用 `<run-output>/stage-events.jsonl`，每个事件 append 后 fsync。事件顺序固定为 process binding、frame start、EXR written/reopened、pixel projected、PNG written、pixel report written、run report written。
4. 首个 nonzero、signal、timeout、缺失 terminal receipt 或 ledger 顺序错误后立即停止，不启动后续 case；partial output、日志与 ledger 全部保留。
5. v0.2 只能使用机器可读 C1 中三条 fresh/disjoint roots。

## 不允许修改

C1 不是算法或质量修正。不得改变三镜头、三帧、A/B、64 spp、分辨率、Cycles CPU、OCIO、decoded Combined exact 判据、进程/渲染上限、16 gates、10 attacks、timeout、disk/bytes ceiling 或 claim boundary。若 v0.2 揭示实际像素算法错误，必须保留 v0.2 并另行预注册下一 correction。

## 下一步

先把 C1、v0.1 完整失败树与 journal 提交推送。之后才允许修改三个 candidate tools和 render script；v0.2 preflight root 在修正工具 freeze 推送前不得创建。
