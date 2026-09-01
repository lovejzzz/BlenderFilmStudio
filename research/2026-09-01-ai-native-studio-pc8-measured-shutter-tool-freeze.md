# PC8 measured shutter 工具冻结

C1 修正后的产品提交是 `9d5a66869528b66216b977c01312cdc849f28fad`，相对已发布
PC7 基线只修改 `film_studio_causal.py`，120 additions / 16 deletions。开发回放逐值复现
PC7 的五组初始条件和完整 physics record；v0.2 兼容路径保持 motion blur disabled 且不
产生 cinematography result。v0.4 从相同物理得到 median `19.61656045 px/frame`、computed
shutter `0.30586402 frame` 和 target error `4e-8 px`。sharp/measured A/B 直接观察可见
速度差，同时保留五个目标、面板、横带和接触方向。

正式工具在 attempt-01 fresh roots 中进行一次 clean native arm64 build、16 个 authority
negative controls、三次产品启动、一份 sharp impact control、三张产品 still、24 张
measured-shutter clip frame、一次 save/reopen 和一次无 Blender 独立审计。审计单独重算
variation basis、median、shutter，并要求 PC8 完整 physics record 等于 accepted PC7
`build.json`。工具冻结后不允许再修改；失败必须保留新 root，不能降低 exact physics、
shutter、视觉或资源门槛。
