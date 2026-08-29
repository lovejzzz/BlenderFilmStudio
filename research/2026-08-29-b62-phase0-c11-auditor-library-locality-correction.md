# B62-P0-E1-C11：auditor library locality 更正

Date: 2026-08-29

Status: **preregistered after D6 PASS, before production-auditor change and D7**

D6用retained v0.3 master证明其初始library与linked ID均为零。三份asset经`link=False` append产生54/84/16个tracked IDs，全部`.library=null`；每次只有一个descriptor且精确指向该asset源文件。删除descriptor不影响local IDs，清理后library、linked-ID和tracked rosters全部exact复原。

C11只允许修改独立production auditor：master外链门必须读取任何append前的immutable snapshot；asset安全门必须直接验证appended ID locality、descriptor exact-source、descriptor removal survival与cleanup exact。原有23 checks、identity/topology/rig/action/contact/camera/render/EXR逻辑均保留。

修改后先运行D7 one-Blender/zero-render smoke，从retained v0.3只读重开所有产物，将新audit写入独立D7 root。D7必须23/23并由Node独立复核；v0.3原audit和INVALIDATED verdict不得覆盖。只有D7 PASS才允许另行预注册fresh formal retry。
