# RC6 最终分辨率静态确认 attempt-25 失败

`RC6-2026-09-01-source-clearance-final-attempt-25` 保留为 `FAIL_EXECUTION`。Blender 启动一次并在约 `0.37 s` 内于任何 Mantaflow data/mesh bake、`.blend` 保存或渲染之前停止。

失败原因是外层 final scene wrapper 直接在 C1 wrapper 的 Python 源码中寻找底层组合后场景源码里的 resolution assertion。该字符串只存在于 C1 wrapper 运行时生成的 `source` 变量中，因此冻结的唯一目标计数为零并触发 fail closed。

Blender 进程自身返回 0，但 stderr 含明确 Python traceback。顶层 runner 正确地将“非空 stderr”判为失败；不得把 Blender exit code 单独当成成功证据。

修正只能在 C1 wrapper 完成场景源码组合之后、最终 `exec` 之前，对运行时 `source` 进行唯一替换；必须使用 fresh attempt-26 work/evidence roots。不得覆盖 attempt-25，也不得复用其 user root。
