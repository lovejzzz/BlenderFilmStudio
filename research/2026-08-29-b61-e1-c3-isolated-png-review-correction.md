# B61-E1-C3：isolated PNG review scene修正预注册

日期：2026-08-29

状态：PREREGISTERED

D4真实Blender probe复现active production scene只允许`OPEN_EXR_MULTILAYER`，同时证明isolated scene可配置PNG并由`Image.save_render`写出有效2×2 PNG，production settings exact不变。

C3只允许render script创建一个process-local临时review scene，复制production scene的display device、view transform、look、exposure与gamma，设置PNG/RGBA/8-bit，并把它作为`Render Result.save_render`的scene参数。生产scene完成EXR配置后不得再改变image settings；临时scene必须在finally删除。

Node tools只绑定C3/D4/v0.3 failure并改用fresh v0.4 roots。EXR、OIIO projection、A/B exact、渲染矩阵、16 gates、10 attacks、资源上限全部不变；PNG仍不进入技术verdict。
