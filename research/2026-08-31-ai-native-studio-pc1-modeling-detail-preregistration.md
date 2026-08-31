# PC.1：建模细化增量预注册

Date: 2026-08-31
Status: `PREREGISTERED_BEFORE_PC1_SCENE_MUTATION`

PC.0 已量化owner指出的粗糙建模：大量hero meshes共享低复杂度primitive footprint，12个材质均只有2 nodes，且0 modifiers。PC.1不改摄影机和灯光，而是在guardian、console、core上加入冻结的26个可命名部件与3个新材质区域。

Formal attempt最多2次background Blender start、6次EEVEE render（frame 48/144/240各一对baseline/derived）、1次derived scene save；frozen source save为0。至少12个semantic details、3个material regions、2/3 protected views必须同时达到changed-pixel fraction与mean absolute RGB difference门槛。全部九个sentinel frames的camera transform/lens和light transform/energy/color必须canonical exact，action/keyframe roster不变。

工具与fresh roots在首次PC.1 start前另行冻结。Machine visible-change PASS只证明细节进入受保护画面，不等于审美更好；综合审美判断留到PC.3 delayed human A/B review。
