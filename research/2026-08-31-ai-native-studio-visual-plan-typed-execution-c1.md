# PC4-VX1 C1：Blender 5.2 layered Action API

Attempt-01 在第一个 visibility operation 内为两个目标插入内存 keyframe 后，尝试通过已移除的 `Action.fcurves` 设置 CONSTANT interpolation，Blender 5.2 返回 `AttributeError`。停止点早于任何 derivative save 或 render；source SHA 保持 `339de003…`，work root 为空。

C1 只允许：

- 将 fcurve 遍历从 `action.fcurves` 改为 Blender 5.2 的 `action.layers → strips → channelbags → fcurves`；
- 将 context/freeze 绑定升级到 v0.2 和 fresh attempt-02 roots；
- 修正后仍必须在 reopen 验证 frame 48 hidden、frame 97 restored。

Plan、target roster、五个 typed adapters、12% lens policy、bounding-box geometry、28-part floor、光影保护、三张 review frame 和全部资源阈值保持不变。Attempt-01 evidence root 与空 work root不得修改或清理。

