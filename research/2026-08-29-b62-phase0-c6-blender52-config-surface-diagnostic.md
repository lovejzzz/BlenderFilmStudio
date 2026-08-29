# B62-P0-E1-C6：Blender 5.2 配置表面诊断

Date: 2026-08-29

Status: **preregistered after retained v0.2 failure, before D3**

v0.2越过了multilayer EXR赋值，但generator随后在`view_settings.look = Medium High Contrast`退出。冻结OCIO下运行时只报告`None`与`ACES 1.3 Reference Gamut Compression`；v0.2仍为one Blender/zero render失败，必须保留。

为避免再逐枚举试错，C6预注册D3 one-Blender/zero-render配置表面探针。它在正式OCIO环境同时验证runtime-exact display/view、旧look reject与neutral None accept、Cycles CPU/64/denoise/fixed seed、Eevee Next/16 final samples、motion blur及MLEXR/HALF/ZIP。

只有全部PASS才允许用`display=sRGB - Display`、`view=ACES 2.0 - SDR 100 nits (Rec.709)`、`look=None`覆盖父合同中的显示名称。该override是运行时兼容的neutral transform；禁止在看到像素后增加补偿grade。Phase 0本就不宣布cinematic grading quality。后续retry必须使用全新v0.3 roots，正式预算与claim boundary不变。
