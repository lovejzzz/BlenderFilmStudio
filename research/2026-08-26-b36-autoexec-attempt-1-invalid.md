# B36 attempt 1 · runtime identity comparison invalidated the run

日期：2026-08-26（America/New_York）

状态：**`IDENTITY_OR_DESIGN_INVALID_BEFORE_ATTACKS`**

预注册 commit `541e0a7` 与工具冻结 commit `76f7402` 之后，B36 第一次运行创建了受控 registered-Text `.blend`，随后启动六个唯一的真实 Blender 5.2 进程。

## 实际观察

- ENABLE_A / B 都写出 marker，token 精确，marker PID 等于 trusted probe PID；
- DISABLE_A / B 与 FACTORY_DEFAULT_A / B 都没有 marker；
- 6/6 进程 exit 0、无 timeout、trusted probe 存在；
- 四个未执行 cell 的 `bpy.app.autoexec_fail` 均为 true；两个 ENABLE cell 均为 false；
- source `.blend` 运行前后 SHA-256 相同；
- 其他冻结 gate 全部为 true。

runner 仍正确返回非零状态并停止在 attacks 之前，因为 `RUNTIME_IDENTITY` 为 false。诊断显示真实 API 值是 `bpy.app.version_string == "5.2.0 LTS"`，build hash 是冻结的 `fbe6228777e7`；spec 也明确冻结 `"5.2.0 LTS"`，但 analyzer 实现错误地把 version string 写死为 `"5.2.0"`。

## 判定

这是 analyzer 的字符串比较实现错误，不是 autoexec 行为结论。第一次输出不能晋级为支持结果，七个 analyzer attacks 未运行，结果原样保留为：

- `experiments/autoexec-boundary-v0-1/attempt-1-invalid.json`
- artifact SHA-256 `e5e8f17ec7d8b4f245175f641c6cea10a5616ad0b384c157359936d9e301ca18`

下一步只允许把 analyzer 的 expected version 修正为 spec 已冻结的完整 `5.2.0 LTS` 字符串；不得改 cell、marker、阈值、decision rules 或已有 evidence。修复必须独立提交，再从新的 run directory 重跑全部六个进程与七个 attacks。
