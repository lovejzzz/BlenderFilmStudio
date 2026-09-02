#!/usr/bin/env python3
"""C2 audit wrapper: normalize only retained failure evidence root label."""

import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().with_name("audit-rc6-liquid-final-effector-mesh-c1.py")
EXPECTED_BASE_SHA256 = "bc4158581af510969e2f8ca735ed067a17503ec8990c3c2d6fe7cfd0f6641847"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256: raise RuntimeError("Mesh C2 audit base identity mismatch")
source = BASE.read_text()
replacements = (
    ('"""Independently audit C1 persisted Data-state Mesh reconstruction."""', '"""Independently audit C2 canonical-path Data-state Mesh reconstruction."""', "docstring"),
    ('RUNNER=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c1.py"; AUDITOR=Path(__file__).resolve(); SPEC=RESEARCH/"specs/ai-native-studio-rc6-liquid-final-effector-mesh-c1-tool-freeze.v0.50.json"', 'RUNNER=RESEARCH/"scripts/run-rc6-liquid-final-effector-mesh-c2.py"; AUDITOR=Path(__file__).resolve(); SPEC=RESEARCH/"specs/ai-native-studio-rc6-liquid-final-effector-mesh-c2-tool-freeze.v0.52.json"', "tool paths"),
    ('    check("retainedFailureExact",manifest(FAILURE_EVIDENCE)["manifestHash"]==spec["retainedFailure"]["evidenceRootManifestHash"] and manifest(FAILURE_WORK)["manifestHash"]==spec["retainedFailure"]["workRootManifestHash"] and read(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]==spec["retainedFailure"]["processHash"],checks)', '    failure_evidence_manifest=manifest(FAILURE_EVIDENCE)\n    failure_evidence_manifest["root"]="experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"\n    failure_evidence_manifest["manifestHash"]=self_hash(failure_evidence_manifest,"manifestHash")\n    check("retainedFailureExact",failure_evidence_manifest["manifestHash"]==spec["retainedFailure"]["evidenceRootManifestHash"] and manifest(FAILURE_WORK)["manifestHash"]==spec["retainedFailure"]["workRootManifestHash"] and read(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]==spec["retainedFailure"]["processHash"],checks)', "canonical failure label"),
)
for before,after,label in replacements:
    if source.count(before)!=1: raise RuntimeError(f"Mesh C2 audit {label} target mismatch")
    source=source.replace(before,after)
exec(compile(source,str(BASE)+"#MESH_C2_AUDIT_V01","exec"),globals(),globals())
