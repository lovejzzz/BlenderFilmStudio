# B62-P0-E1-C7：Blender 5.2 Eevee engine runtime 名称更正

Date: 2026-08-29

Status: **preregistered after retained D3 failure, before D4**

D3依次通过color与Cycles赋值，但在`BLENDER_EEVEE_NEXT`处被Blender拒绝；runtime明确列出`BLENDER_EEVEE / BLENDER_WORKBENCH / CYCLES`。D3因此在写structured marker前exit 1，只保留exact stdout/stderr，不允许补写result。

C7预注册D4，必须显式证明旧engine名称reject、新`BLENDER_EEVEE`accept、16 final samples可写，并继续完成C6全部color/Cycles/motion-blur/EXR checks。只有D4完整PASS才允许同时采用neutral color override与runtime Eevee名称；这只修API标识，不改变Eevee算法、samples、分辨率或预算。
