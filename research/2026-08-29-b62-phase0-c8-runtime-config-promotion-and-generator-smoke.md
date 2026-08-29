# B62-P0-E1-C8：runtime config promotion 与真实 generator smoke

Date: 2026-08-29

Status: **preregistered after D4 PASS, before production-tool change and D5**

D4以9/9证明完整Blender 5.2配置表面：旧look与旧Eevee name按预期reject；neutral ACES display/view/look、`BLENDER_EEVEE`、16 final samples、Cycles fixed dose、motion blur及MLEXR/HALF/ZIP全部accept，zero render。

C8只授权generator明确保存neutral runtime color transform，renderer使用当前Eevee runtime name并校验同一color transform。禁止改变任何视觉资产或render dose。

在正式v0.3前，先运行D5：one Blender、zero render，直接调用冻结后的production generator写入独立diagnostic root。它必须完整产生三份asset libraries、motion library、master blend与valid generation report，并受512 MiB write/100 GiB reserve限制；独立Node audit必须PASS。只有D5通过才允许另行预注册C9正式绑定。
