# PC8 C1：摄影字段不能偷偷重采样物理世界

PC8 v0.1 在正式 root 出现前被开发烟雾测试否定。v0.3 fixture 增加了 measured shutter
字段，因此整个 SceneSpec self hash 改变；产品原有的 deterministic variation 又把这个
self hash 当作随机基底。结果是没有显式修改位置、摩擦或回弹，五个物体的初始微差仍被
全部重采样，后续终局也不再等于 PC7。它违反了已冻结的 primary-physics exact 控制。

这是合同设计问题，不是调参问题。v0.1 preregistration 和 v0.3 fixture 原样保留；正式
attempt-01 仍不存在。C1 v0.2 新增 v0.4 fixture，只在 `deterministicVariation` 中增加
`basisSceneSpecHash`，精确绑定 PC7 fixture hash `b1bcabc7…`。初始微差改由这个独立物理
identity、seed、target index 和 channel 派生；后续摄影、交付或元数据字段变化不再改变
物理世界。

这不是给最终条件开后门。basis 只能参与有界初始微差，仍不能写最终坐标、目标关键帧
或 release 后 actor 姿态。修正后的开发测试必须先逐值复现 PC7 的五组初始条件、响应帧、
final tilts、impact/aftermath 和 zero-pose-key provenance，才能冻结工具和启动正式运行。
