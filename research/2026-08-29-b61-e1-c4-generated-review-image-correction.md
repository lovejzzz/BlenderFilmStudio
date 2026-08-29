# B61-E1-C4：generated float review image修正预注册

日期：2026-08-29

状态：PREREGISTERED

D5在真实Blender 5.2、frozen OCIO下证明：保留EXR的exact OIIO Combined array可填入1920×1080 Blender float image，标记ACEScg，经isolated review scene输出有效PNG；production settings不变，zero render。人工检查确认图像方向与内容可读。

C4只允许`pixel_projection`同时返回其已用于SHA的RGBA array；PNG review从该同一array构造临时float image，做OIIO Y0-top到Blender pixel0-bottom的row conversion，source colorspace固定ACEScg，经C3 review scene保存并在finally删除。禁止读取无data的Render Result，禁止二次解码EXR。

Node supervision只绑定C4/D5/v0.4 failure并改用fresh v0.5 roots；每帧报告新增generated-float-image、ACEScg和row-order exact声明。EXR、digest、渲染矩阵、技术门和资源阈值不变。
