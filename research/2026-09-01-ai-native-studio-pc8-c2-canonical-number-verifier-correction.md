# PC8 C2：主机自哈希数字规范修正

## 结论

PC8 attempt-01 尚未开始。冻结的 v0.1 主机 runner 在创建任何正式 work/evidence root、原生构建或启动产品前失败。失败不是物理、镜头或产品实现问题，而是主机验证器把 C1 中的 `0.000001` 用 Python 默认形式序列化为 `1e-06`；C1 自哈希原本按照 JavaScript `JSON.stringify` 的 `0.000001` 计算。

C2 仅修正这一处主机自哈希验证，并复用 `blender/compile_scene.py` 已有的 JavaScript 有限数字表示边界。原冻结 runner/auditor 保持逐字不变，C2 通过小型版本化启动器在内存中装配修正。

## retained failure

- 命令：`python3 scripts/run-pc8-measured-shutter.py`
- 错误：`RuntimeError('PC8 frozen contract differs')`
- Python canonical hash：`db3b7ccb9bdbe40dd28202a53e54557db34a64b49a3ea136ef628bd47fb817b8`
- JavaScript canonical hash：`8110fdbb9263fd7c62eb1997b43b6fe92d768bdbae04ddc5aae23f89de74b6ab`
- 正式 workspace root：不存在
- 正式 evidence root：不存在
- 原生构建：0
- 产品启动：0

## 不变项

- C1 语义预注册、v0.4 fixture、产品源码提交与产品模块均不变。
- PC7 的初始条件与 Bullet 求解 exact non-regression 不变。
- 目标模糊像素、测量算法、shutter 范围、直接 A/B 复核要求均不变。
- 正式 roots、资源上限、进程/渲染/保存次数均不变。

## C2 bindings

- correction spec：`specs/ai-native-studio-pc8-measured-shutter-c2-preregistration.v0.3.json`
- corrected runner：`scripts/run-pc8-measured-shutter-c2.py`
- corrected auditor：`scripts/audit-pc8-measured-shutter-c2.py`
- corrected freeze：`specs/ai-native-studio-pc8-measured-shutter-tool-freeze-c2.v0.2.json`

任何正式 root 在 C2 启动前出现，或任何产品、fixture、阈值绑定变化，都必须停止。
