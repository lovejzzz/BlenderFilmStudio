# PC5 C2：宿主 EEVEE 枚举

Attempt-02 证明 C1 的语义退出闸门有效：Blender 即使在 Python exception 后返回 exit 0，runner 仍因没有 success marker/artifact 且 stderr 含 traceback 而立即停止；reopen start 为零。独立失败审计保留 exact host enum roster：`BLENDER_EEVEE`、`BLENDER_WORKBENCH`、`CYCLES`。

C2 只把 scene render engine 从该宿主不存在的 `BLENDER_EEVEE_NEXT` 改为同一内置实时渲染器的可用 enum `BLENDER_EEVEE`。不改变任何模型、刚体、质量、速度、摩擦、阻尼、灯光、相机、render resolution、物理/视觉门槛或资源上限。Attempt-03 使用 fresh roots；attempt-01/02 不变。
