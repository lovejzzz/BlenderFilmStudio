# B61-E1-D5：generated 1080p review image诊断预注册

日期：2026-08-29

状态：PREREGISTERED

v0.4证明isolated review scene有效，但headless `write_still=True`之后的`Render Result`没有可供`save_render`使用的image data。OIIO Combined RGBA数组仍完整且digest exact。

D5允许一个Blender start、零render：用冻结的OIIO算法解码保留EXR，要求`192237bd…`；从该exact 1920×1080×4 float array创建临时Blender float image；通过D4已证明的isolated review scene保存PNG；验证1920×1080 header，删除临时image/scene并要求production settings不变。不得改变EXR或像素判据。

D5 PASS只授权另行预注册C4，不直接授权formal retry。
