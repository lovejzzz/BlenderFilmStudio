# B61-E1-D4：PNG review export context诊断预注册

日期：2026-08-29

状态：PREREGISTERED

B61 v0.3已通过EXR write、OIIO reopen与pixel projection，最后在把active production scene的`image_settings.file_format`从`OPEN_EXR_MULTILAYER`改为`PNG`时被Blender 5.2拒绝。PNG只用于人工review，不参与技术verdict，但不能静默丢失。

D4允许一个Blender background start、零render call。它在同一production blend中记录active scene的格式枚举并复现assignment failure；随后创建独立临时review scene，验证其可设置PNG，并用2×2 generated float image调用`save_render(..., scene=review_scene)`写出有效PNG；最后要求production scene所有render/image settings exact不变并删除临时数据。

D4不读取或修改formal EXR，不重跑Cycles，不测试电影感。只有PASS才能另行预注册C3，把正式PNG export改为临时review scene；D4本身不授权v0.4 formal retry。
