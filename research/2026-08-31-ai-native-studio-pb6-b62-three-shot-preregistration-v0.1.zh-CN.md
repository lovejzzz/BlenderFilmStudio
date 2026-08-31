# PB.6 B62 三镜头垂直切片预注册 v0.1

PB.5 已关闭 `PASS`。PB.6 不重新发明 B62，也不把历史演示直接冒充产品输出；它把已经独立审计的 terminal scene package 纳入 Film Studio 产品工作流，并从 exact source `.blend` 生成一份全新的 288 帧三镜头 review animatic。

产品增量仍只允许三个既有 Python 路径、最多 500 additions、零 C/C++。可见操作为 `Build B62 Review Animatic`，typed state 必须显示 slice status、current shot、completed frames、shared identity 与 frame-288 historical boundary。模型没有生成 Python、shell 或任意 filesystem 权限。

三镜头固定为 WIDE 1–96 / `CAM_WIDE_APPROACH`、MEDIUM 97–192 / `CAM_MEDIUM_CONTACT`、CLOSE 193–288 / `CAM_CLOSE_MOTION_TERMINAL`。它们必须来自同一 exact source blend，并共享 guardian、console/core、observatory 的冻结 asset/material/topology/action/contact/light/provenance identity；只有 timeline-selected camera 随 shot 变化。

正式序列最多一次 clean arm64 build、四次产品启动、288 次 EEVEE render 与一次本地 ffmpeg。第一启动零渲染检查合同；第二启动通过可见产品 operator 生成全新 288 张 640×360 PNG；随后生成 24 fps MP4；第三启动零渲染 reopen；第四启动以零渲染执行五个攻击并由不导入产品模块的 auditor 独立重解码。Inherited T2 frames 不得复制为 PB.6 输出。

最重要的不可放宽边界是 retained D4 frame 288：`clampedUnionAreaFraction=0.93378717684983`，冻结 maximum `0.90`，结论仍是 `B62_CLOSE_CAMERA_CORRECTION_FAILS_FROZEN_HOLDOUT`。后续 motion-aware camera 在相同 0.90 门槛下通过是另一条证据，不能擦除或改写这个历史拒绝。攻击清单显式包含删除 frame-288 rejection 与把 0.90 放宽到 0.91，两者必须在渲染前拒绝。

Fresh external/evidence roots 上限 2 GiB / 512 MiB。100 GiB reserve 加 12 GiB build 与 1 GiB formal output 后，准入要求为 121,332,826,112 bytes。零 network/model/mouse；零 release、binary distribution、LFS upload、force/other refs、sign/notary；PB.7 不启动。

即使 PASS，结论也只覆盖一个继承的 stylized B62 scene、一台 admitted arm64 host 与一份 640×360 review animatic。人类审片状态保留为 `PENDING_UNTIL_PB7`，不得扩写为最终电影质量、photorealism、production readiness 或 autonomous filmmaking。
