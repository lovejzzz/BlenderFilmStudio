#!/usr/bin/env python3
"""C3 Mesh scene wrapper over the persisted-state C1 implementation."""

import hashlib
from pathlib import Path

BASE=Path(__file__).resolve().with_name("run-rc6-liquid-final-effector-mesh-c1-scene.py")
EXPECTED_BASE_SHA256="c6ff9e4f72559043ca4b17ef7973cce2f1a30b85d4763452a78da42ea2e3ab5c"
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=EXPECTED_BASE_SHA256:raise RuntimeError("C3 Mesh scene base identity mismatch")
source=BASE.read_text()
for before,after,expected,label in (
    ('"final-effector-mesh-c1": 9.0','"final-effector-mesh-c3": 9.0',1,"cell"),
    ('bfs.rc6LiquidFinalEffectorMeshC1Cell.v0.1','bfs.rc6LiquidFinalEffectorMeshC3Cell.v0.1',1,"schema"),
    ('RC6_FINAL_EFFECTOR_MESH_C1=','RC6_FINAL_EFFECTOR_MESH_C3=',1,"marker"),
):
    if source.count(before)!=expected:raise RuntimeError(f"C3 Mesh scene {label} target mismatch")
    source=source.replace(before,after)
exec(compile(source,str(BASE)+"#MESH_C3_V01","exec"),globals(),globals())
