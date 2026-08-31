# PB.2 C1：non-circular execution commit binding v0.5

日期：2026-08-31

状态：**工具修正冻结；不扩大已批准 PB.2 validation-only scope**

v0.4 template 要求 execution contract 正文写入“包含该正文的 commit OID”。Git commit OID 又取决于正文，因此这是无法构造的 fixed-point self-reference，不是有效执行门。

C1 保留 v0.3 tool freeze 和所有 B01/B02、八个负控、零权限上限，仅替换 commit identity 证明：execution contract 写入父提交；提交后 runner 验证当前 HEAD 的父提交、当前 HEAD OID、`git show HEAD:<contract>` 与工作树文件 byte-exact，并要求工作树在 fresh-root 创建前 clean。这样同时证明合同已经提交，又不在合同正文中制造自引用。

用户已明确批准链接的 PB.2 validation-only 范围并要求继续。C1 不授权 Blender、render、proposal execution、BuildPlan write、scene mutation、engine source/remote write、LFS、签名、公证、DMG 或 PB.3–PB.7。
