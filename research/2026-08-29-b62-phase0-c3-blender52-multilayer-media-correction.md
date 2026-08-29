# B62-P0-E1-C3：Blender 5.2 multilayer media-type 设置顺序更正

Date: 2026-08-29

Status: **preregistered after retained v0.1 failure, before D1 diagnostic and before retry**

## 正式失败

官方preflight `ad7bc82…`通过后，v0.1 runner依次写入attempt/admission/receipt/formal-start并启动第一个真实Blender generator。进程在0.752秒后exit 1，peak RSS 260,882,432 bytes，render calls 0。错误为factory scene的`ImageFormatSettings.file_format`枚举不包含`OPEN_EXR_MULTILAYER`。

v0.1 attempt保留7 files / 7,519 bytes / tree `f27179c8…`，formal保留5 files / 493,005 bytes / tree `f71e288a…`；failure self-hash为`dc47c06a…`。不得修改或覆盖。

## 可证伪假设与D1

B61在相同Blender build通过同一file-format赋值，但其输入blend已保存multi-layer media状态；B62从factory scene开始。C3假设Blender 5.2必须先将`image_settings.media_type`设为`MULTI_LAYER_IMAGE`，才会暴露并接受`OPEN_EXR_MULTILAYER`。

先允许一个独立D1 Blender start、zero render，在factory state记录默认枚举，证明错误顺序拒绝、正确顺序接受，并确认HALF/ZIP仍可设置。D1只可写自哈希result/receipt与两份日志。

只有D1 PASS才允许在generator与renderer的每个multilayer EXR赋值前显式写`media_type = MULTI_LAYER_IMAGE`，并在calibration report中记录mediaType。不得改变创作内容、frames、64 spp、seed、denoise、1080p、ZIP、预算、gates、attacks或verdict。

重试必须使用新的preflight/attempt/formal v0.2 roots；正式六次Blender/291 renders预算不含D1且保持不变。
