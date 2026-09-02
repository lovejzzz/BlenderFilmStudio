#!/usr/bin/env python3
"""C3 independent audit wrapper for post-configuration Data materialization."""

import hashlib
from pathlib import Path

BASE=Path(__file__).resolve().with_name("audit-rc6-liquid-final-effector-mesh-c1.py")
EXPECTED_BASE_SHA256="bc4158581af510969e2f8ca735ed067a17503ec8990c3c2d6fe7cfd0f6641847"
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=EXPECTED_BASE_SHA256:raise RuntimeError("C3 audit base identity mismatch")
source=BASE.read_text()
replacements=(
    ('"""Independently audit C1 persisted Data-state Mesh reconstruction."""','"""Independently audit C3 staged Data materialization and Mesh reconstruction."""',"docstring"),
    ('FAILURE_EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"; FAILURE_WORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-attempt-44")\nWORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"); EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"; CELL_ID="final-effector-mesh-c1"','FAILURE_EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"; FAILURE_WORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c1-attempt-45")\nWORK=Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-c3-attempt-46"); EVIDENCE=RESEARCH/"experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c3-attempt-46"; CELL_ID="final-effector-mesh-c3"',"roots"),
    ('ADOPT_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1-adopt-scene.py"; MESH_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1-scene.py"; RUNNER=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1.py"; AUDITOR=Path(__file__).resolve(); SPEC=RESEARCH/"specs/ai-native-studio-rc6-liquid-final-effector-mesh-c1-tool-freeze.v0.50.json"','ADOPT_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c3-adopt-scene.py"; MESH_TOOL=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c3-scene.py"; RUNNER=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c3.py"; AUDITOR=Path(__file__).resolve(); SPEC=RESEARCH/"specs/ai-native-studio-rc6-liquid-final-effector-mesh-c3-tool-freeze.v0.54.json"',"tools"),
    ('    check("retainedFailureExact",manifest(FAILURE_EVIDENCE)["manifestHash"]==spec["retainedFailure"]["evidenceRootManifestHash"] and manifest(FAILURE_WORK)["manifestHash"]==spec["retainedFailure"]["workRootManifestHash"] and read(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]==spec["retainedFailure"]["processHash"],checks)','    failure_evidence_manifest=manifest(FAILURE_EVIDENCE)\n    failure_evidence_manifest["root"]="experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-c1-attempt-45"\n    failure_evidence_manifest["manifestHash"]=self_hash(failure_evidence_manifest,"manifestHash")\n    check("retainedFailureExact",failure_evidence_manifest["manifestHash"]==spec["retainedFailure"]["evidenceRootManifestHash"] and manifest(FAILURE_WORK)["manifestHash"]==spec["retainedFailure"]["workRootManifestHash"] and read(FAILURE_EVIDENCE/"processes/01.json")["processHash"]==spec["retainedFailure"]["processHash"],checks)',"failure"),
    ('"RC6_FINAL_EFFECTOR_MESH_C1="','"RC6_FINAL_EFFECTOR_MESH_C3="',"marker"),
    ('adoption["authority"]=={"cacheStateAdoptions":1,','adoption["authority"]=={"stagedDataMaterializations":1,"cacheStateAdoptions":1,',"adoption authority"),
    ('result["schemaVersion"]=="bfs.rc6LiquidFinalEffectorMeshC1Cell.v0.1"','result["schemaVersion"]=="bfs.rc6LiquidFinalEffectorMeshC3Cell.v0.1"',"mesh schema"),
    ('("PASS_FINAL_EFFECTOR_MESH_C1_STATIC" if scientific else "FAIL_FINAL_EFFECTOR_MESH_C1_STATIC")','("PASS_FINAL_EFFECTOR_MESH_C3_STATIC" if scientific else "FAIL_FINAL_EFFECTOR_MESH_C3_STATIC")',"verdict"),
    ('{"blenderStarts":2,"cacheStateAdoptions":1,','{"blenderStarts":2,"stagedDataMaterializations":1,"cacheStateAdoptions":1,',"counts"),
    ('bfs.rc6LiquidFinalEffectorMeshC1IndependentAudit.v0.1','bfs.rc6LiquidFinalEffectorMeshC3IndependentAudit.v0.1',"audit schema"),
)
for before,after,label in replacements:
    if source.count(before)!=1:raise RuntimeError(f"C3 audit {label} target mismatch")
    source=source.replace(before,after)
exec(compile(source,str(BASE)+"#MESH_C3_AUDIT_V01","exec"),globals(),globals())
