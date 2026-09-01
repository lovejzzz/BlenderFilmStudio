# 从“加零件”到“理解关系”：Visual Film Language v0.2

PC4-VX1 attempt-03 的机器侧为 25/25 PASS，但直接截图判断为视觉失败。这个反例证明：typed operation、provenance、part count 和 layer floor 可以保证执行可控，却不能保证画面好看。

v0.2 把失败转成跨作品约束，而不是继续为 PC4 写坐标补丁：非叙事前景对主体轮廓的遮挡率、主体负空间 margin、画面 occupancy interval、附加细节的 contour relief depth、screen-space coverage、primary/secondary/tertiary scale bands，以及 `EYE_LINE → BROW → CHEEK → JAW` 面部 landmark hierarchy。Catalog 只提供这些关系的冻结参数，assessment 只描述可见问题，plan 不携带 Python、shell、network 或任意 filesystem authority。

新 compiler 同时绑定被拒绝的 observed scene 与最后接受的 clean execution baseline。这样软件能从失败截图学习，却从干净基线重建，避免把错误几何继续叠加。八项新 contract test 与十九项 v0.1 regression test 全部通过；compiler 与 catalog 均不含 PC4、B62 或项目 ID 的特殊分支。

这仍不是“软件已会自动看图”。它证明的是更重要的中间能力：视觉教师的判断可以被保存为通用电影语言，并确定性编译为受约束、不可执行的改进计划。下一门课是让 typed executor 测量并服从这些关系，而不是满足部件数量。
