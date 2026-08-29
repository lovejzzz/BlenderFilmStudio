# B62-P0-E1-C4：动态 EXR setter A/B/A 更正

Date: 2026-08-29

Status: **preregistered after retained D1 FAIL, before D2**

D1的实际赋值行为支持C3：`IMAGE`下`OPEN_EXR_MULTILAYER` setter拒绝，改为`MULTI_LAYER_IMAGE`后接受，HALF/ZIP也接受。但D1预注册错误地要求`bl_rna.enum_items`在A状态不列出multilayer；Blender返回静态superset，因此8门中1门false，D1整体必须保留为FAIL。

C4不把D1改判。它将错误测量明确为static RNA metadata，并预注册D2 one-Blender/zero-render动态A/B/A实验。每个repetition都必须观察：A=`IMAGE`时赋值reject；B=`MULTI_LAYER_IMAGE`时赋值accept；再切回A时赋值reject。共3 repetitions/9 setter outcomes，判决完全忽略enum-items列表。

只有9/9及最终MULTI_LAYER_IMAGE/OPEN_EXR_MULTILAYER/HALF/ZIP全部exact，才授权C3限定的两份production Blender工具修改和v0.2 roots。正式预算、创作合同、18 gates、16 attacks与claim boundary不变。
