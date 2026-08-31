# PC.0 read-only hero asset/action inventory：tool freeze

Date: 2026-08-31

Status: `FROZEN_BEFORE_PC0_START`

PC.0 将用 accepted PB.6 arm64 binary 打开 exact B62 source blend，一次性读取完整 object/mesh/material/modifier/constraint/action/F-curve/keyframe roster，以及九个 sentinel frames 的 object、pose、camera 和 light state。Probe 不包含 render、save、network 或 subprocess 调用。

Static validation 已通过 Python AST、三个 Node syntax checks、forbidden-pattern count 0 和 synthetic inventory/attack checks 14/14。Runner 只接受 preregistered spec/tool/root 参数，先验证 source/binary/tool hashes 和 fresh roots，再通过 `/usr/bin/time -l` 启动一次 Blender。Auditor 独立复核所有 roster/totals、process streams、RSS/wall ceilings、source immutability 和全 evidence/work roots 零 render artifacts。

Formal evidence root 与 external work root 在冻结时均不存在。上限保持 1 Blender start、0 render、0 save、0 engine edit/commit/push、0 network/model/mouse；evidence 16 MiB、work 64 MiB、wall 300 秒、peak RSS 2 GiB。任何失败保留，PC.0 audit PASS 前不得开始 PC.1。
