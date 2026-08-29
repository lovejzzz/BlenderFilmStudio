# B62-P0-E1-C10：library locality 诊断

Date: 2026-08-29

Status: **preregistered after retained v0.3 failure, before D6 tools**

v0.3完成generator、288帧Eevee animatic、ffmpeg/ffprobe和三张1080p/64 spp Cycles calibration，总计291 render calls。独立Blender auditor的23项检查有21项通过，只因`masterExternalLibrariesZero`与`assetLibrariesSafe`失败而整体INVALIDATED。三份asset的identity/topology/rig均与generation manifest exact，唯一finding都同为`EXTERNAL_LIBRARY`。

当前auditor在三次`link=False` append之前没有冻结master library roster，却在append之后判定master是否零library；同时把append操作新出现的任何`bpy.data.libraries` descriptor直接当成asset外链，没有检查被追加ID自身的`.library` ownership。C10不把这解释成bug，而预注册D6 one-Blender/zero-render locality probe。

D6必须在任何append前记录master与全部ID ownership；逐asset记录append前/中/后library descriptor和collection/object/mesh/armature/material ownership；移除source descriptor后确认local IDs是否仍存活；最后清理并要求roster exact复原。只有“master初始零library、全部appended IDs为local、descriptor只指向exact source、移除descriptor不破坏local IDs、cleanup exact”同时成立，才允许另行预注册auditor-only更正。

人工抽查同时发现retained frame 240 close shot大面积被前景遮挡、构图较弱。它不是当前machine gate，不能用来改变v0.3机器判决；后续需要独立camera-quality实验。
