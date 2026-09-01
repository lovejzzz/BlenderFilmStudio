# RC1-C3：正式构建后的产品包改名修正

RC1 attempt-01 的本地克隆、LFS 物化与一次干净原生构建均成功。失败发生在构建完成后的路径检查：Blender 的构建系统固定生成 `Blender.app`，而 RC1 运行器直接寻找 `Film Studio Engine F0.app`。因此没有启动产品、没有执行场景、没有渲染、没有保存。

这不是产品源码失败。已接受的 PC9 正式运行器在同一位置执行过一个受限改名：仅当 fresh build root 中 `Blender.app` 存在且 `Film Studio Engine F0.app` 不存在时，把前者改名为后者，再解析内部二进制。RC1-C3 只允许在 fresh attempt-02 重用这一动作。

attempt-02 不得复用 attempt-01 的构建产物，不得修改产品提交 `0e84ef3b6f79521b4f21a9d12a180dfd9713aab4`、fixture、物理参数、镜头规则、阈值、计数或视觉问题。attempt-01 的 work/evidence roots 保留不变并由 failure hash 交叉绑定。
