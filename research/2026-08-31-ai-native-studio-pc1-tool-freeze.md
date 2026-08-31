# PC.1 modeling-detail tools：freeze

Date: 2026-08-31
Status: `FROZEN_BEFORE_PC1_START`

Published preregistration v0.1错误使用了accepted runtime明确拒绝的旧enum `BLENDER_EEVEE_NEXT`。PC.1尚未启动；C1 v0.2只把`/renderProfile/engine`改为runtime-proven `BLENDER_EEVEE`并逐项绑定base，其余inputs/thresholds exact。

Builder、reopen semantic/pixel auditor、two-start runner与final independent auditor已冻结并只绑定C1。Builder先以frames 48/144/240渲染baseline，再加入exact 26-component roster与three procedural material regions，保存一次fresh derived blend并渲染三张derived still。Second start只reopen并复核semantic metadata、material node counts、object/polygon growth、action exactness和A/B pixel metrics，不render/save。

Final auditor独立复核所有self/file hashes、process streams、six PNG roster、source immutability、operations与resource ceilings，并最后写root manifest。Formal roots在freeze时均absent。PC.2仍禁止。
