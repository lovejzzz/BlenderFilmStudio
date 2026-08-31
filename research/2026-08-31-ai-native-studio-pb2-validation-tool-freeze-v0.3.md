# PB.2 validation-only tool freeze v0.3

日期：2026-08-31

状态：**工具已冻结，formal run 未授权、未执行**

PB.2 readiness 19/19 后，本版本把下一次 formal validation 收缩成 pure typed-contract test：系统 Python 直接加载 exact `film_studio_contract.py`，不启动 Blender。B01/B02 各做一次只读 `inspect_proposal`；正例不得写 BuildPlan。八个负例覆盖 rejected、tampered、unapproved、wrong-order、unauthorized-scope、unknown-field、path-escape、nonfinite，并要求调用前后 workspace 文件指纹完全一致。

trusted runner 只能运行固定的 `git rev-parse HEAD` 与 `git status --porcelain=v1` 身份检查；proposal 不能提供命令、Python、网络目标或任意路径。runner 和独立 auditor 均被冻结到 SHA-256，auditor 不导入产品合同模块。

唯一 future work root 与 evidence root 必须在执行前不存在。formal run 上限为 120 秒、64 MiB work root、8 MiB evidence root；Blender、render、proposal execution、BuildPlan write、engine edit、engine remote write、network call 上限全部为零。

`specs/ai-native-studio-pb2-validation-only-authorization-request.v0.3.json` 提供精确授权文本。v0.3 request 和 tool freeze 本身不可执行；只有新的、已提交的 v0.4 execution contract 可以解锁一次 runner。
