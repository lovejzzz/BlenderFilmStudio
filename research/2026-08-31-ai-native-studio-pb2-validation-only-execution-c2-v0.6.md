# PB.2 validation-only execution C2 v0.6

状态：**AUTHORIZED_FOR_ONE_FORMAL_RUN；尚未执行**

本合同绑定用户批准原文、v0.3 base tool freeze、C2 derived-HEAD correction、exact runner/auditor SHA、唯一 fresh roots、B01/B02 两次只读 inspection 和八个负控。

合同只写已知父提交 `f3a8f869…`，不包含自身 commit OID。提交后 runner 必须证明当前 HEAD 的父提交匹配、当前 HEAD 包含 exact contract bytes、工作树 clean，然后才能加载产品合同模块和创建 roots。

Blender、render、proposal execution、BuildPlan write、scene mutation、engine source/remote write、network 和 PB.3–PB.7 仍全部为零或未授权。
