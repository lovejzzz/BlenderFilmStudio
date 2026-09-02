#!/usr/bin/env python3
"""C2 wrapper: normalize only retained failure evidence root label."""

import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().with_name("run-rc6-liquid-final-effector-mesh-c1.py")
EXPECTED_BASE_SHA256 = "58562de9fe0a24e3e9c9a2cbc39b64fc56be1624bb8b43b81080af883d541f0b"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256: raise RuntimeError("Mesh C2 runner base identity mismatch")
source = BASE.read_text()
replacements = (
    ('"""Persist verified Data state, reopen it, and run one Mesh-only reconstruction."""', '"""C2: persist verified Data state after canonical retained-failure path binding."""', "docstring"),
    ('AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-effector-mesh-c1.py"; SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-mesh-c1-tool-freeze.v0.50.json"', 'AUDITOR = RESEARCH / "scripts/audit-rc6-liquid-final-effector-mesh-c2.py"; SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-mesh-c2-tool-freeze.v0.52.json"', "tool paths"),
    ('    if manifest(FAILURE_EVIDENCE)["manifestHash"]!=spec["retainedFailure"]["evidenceRootManifestHash"] or manifest(FAILURE_WORK)["manifestHash"]!=spec["retainedFailure"]["workRootManifestHash"] or read_json(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]!=spec["retainedFailure"]["processHash"]: raise RuntimeError("C1 retained failure drift")', '    failure_evidence_manifest=manifest(FAILURE_EVIDENCE)\n    failure_evidence_manifest["root"]="experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"\n    failure_evidence_manifest["manifestHash"]=self_hash(failure_evidence_manifest,"manifestHash")\n    if failure_evidence_manifest["manifestHash"]!=spec["retainedFailure"]["evidenceRootManifestHash"] or manifest(FAILURE_WORK)["manifestHash"]!=spec["retainedFailure"]["workRootManifestHash"] or read_json(FAILURE_EVIDENCE/"processes/01-final-effector-mesh.json")["processHash"]!=spec["retainedFailure"]["processHash"]: raise RuntimeError("C2 retained failure drift")', "canonical failure label"),
)
for before,after,label in replacements:
    if source.count(before)!=1: raise RuntimeError(f"Mesh C2 runner {label} target mismatch")
    source=source.replace(before,after)
exec(compile(source,str(BASE)+"#MESH_C2_V01","exec"),globals(),globals())
