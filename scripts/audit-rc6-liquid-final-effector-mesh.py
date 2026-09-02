#!/usr/bin/env python3
"""Independently audit the Final effector Mesh-only confirmation."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
RETAINED_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-data-attempt-42")
RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-data-attempt-42"
RETAINED_CACHE = RETAINED_WORK / "final-effector-plus1/mantaflow-cache"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-final-effector-mesh-attempt-44")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-final-effector-mesh-attempt-44"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-final-effector-mesh-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-final-effector-mesh.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-final-effector-mesh-tool-freeze.v0.48.json"
CELL_ID = "final-effector-mesh"
BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"))
def self_hash(value, field):
    body = dict(value); body.pop(field, None); return hashlib.sha256(canonical(body).encode()).hexdigest()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read_json(path): return json.loads(path.read_text())
def check(label, condition, checks): checks[label] = bool(condition)


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink() and str(path.relative_to(root)) not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}; value["manifestHash"] = self_hash(value, "manifestHash"); return value


def expected_data_files(): return sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 8)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)])
def expected_all_files(): return sorted(expected_data_files() + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)])
def cache_roster(root): return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def data_manifest(root):
    files = [{"path": relative, "bytes": (root / relative).stat().st_size, "sha256": sha(root / relative)} for relative in expected_data_files()]
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}; value["manifestHash"] = self_hash(value, "manifestHash"); return value


def expected_argv(data_hash):
    return [str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode", str(WORK / CELL_ID / "source-state.blend"), "--python", str(SCENE_TOOL), "--", "--cell-id", CELL_ID, "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--mesh-particle-radius", "9.0", "--retained-data-manifest-hash", data_hash]


def signed_topology_passes(result, thresholds):
    for sample in result["samples"]:
        positive = [item for item in sample["components"] if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in sample["components"] if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != thresholds["requiredPositiveWaterBodiesPerFrame"] or len(negative) > thresholds["maximumNegativeNestedShellCount"] or any(item["nonManifoldEdgeCount"] for item in sample["components"]): return False
        outer = positive[0]
        for inner in negative:
            if any(inner["boundsMinWorld"][axis] < outer["boundsMinWorld"][axis] - 1e-7 or inner["boundsMaxWorld"][axis] > outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3)): return False
            if sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5 > thresholds["maximumNestedCentroidSeparationMeters"]: return False
    return True


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists(): raise RuntimeError("Final effector Mesh audit path is not fresh")
    spec = read_json(SPEC); admission = read_json(EVIDENCE / "admission.json"); process = read_json(EVIDENCE / "processes/01-final-effector-mesh.json"); result = read_json(EVIDENCE / f"cells/{CELL_ID}/result.json"); receipt = read_json(EVIDENCE / "receipt.json")
    retained_work_manifest = read_json(RETAINED_EVIDENCE / "work-manifest.json"); retained_receipt = read_json(RETAINED_EVIDENCE / "receipt.json"); retained_audit = read_json(RETAINED_EVIDENCE / "independent-audit.json"); retained_data = data_manifest(RETAINED_CACHE)
    stdout_path = EVIDENCE / "logs/01-final-effector-mesh.stdout.log"; stderr_path = EVIDENCE / "logs/01-final-effector-mesh.stderr.log"; copied_cache = WORK / CELL_ID / "mantaflow-cache"; checks = {}
    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("toolRosterExact", spec.get("tools") == {str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL), str(RUNNER.relative_to(RESEARCH)): sha(RUNNER), str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR)}, checks)
    check("inputsExact", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"] and sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"] == admission["sourceBlendSha256"], checks)
    check("retainedEvidenceAndWorkExact", manifest(RETAINED_WORK) == retained_work_manifest and retained_work_manifest["manifestHash"] == spec["inputs"]["retainedWorkManifestHash"] and retained_receipt["receiptHash"] == spec["inputs"]["retainedReceiptHash"] and retained_audit["auditHash"] == spec["inputs"]["retainedAuditHash"] and retained_audit["status"] == "PASS", checks)
    check("retainedAndCopiedDataExact", retained_data["manifestHash"] == spec["inputs"]["retainedDataManifestHash"] == admission["retainedDataManifestHash"] and data_manifest(copied_cache) == retained_data and cache_roster(RETAINED_CACHE) == expected_data_files() and cache_roster(copied_cache) == expected_all_files(), checks)
    check("admissionSelfHash", admission["status"] == "PASS" and admission["admissionHash"] == self_hash(admission, "admissionHash"), checks)
    check("processAndLogsExact", process["processHash"] == self_hash(process, "processHash") and process["argv"] == expected_argv(retained_data["manifestHash"]) and process["exitCode"] == 0 and sha(stdout_path) == process["stdoutSha256"] and sha(stderr_path) == process["stderrSha256"] and stderr_path.stat().st_size == 0 and "RC6_FINAL_EFFECTOR_MESH=" in stdout_path.read_text(errors="replace"), checks)
    config = result["configuration"]
    check("resultAndConfigurationExact", result["schemaVersion"] == "bfs.rc6LiquidFinalEffectorMeshCell.v0.1" and result["status"] == "MEASURED" and result["resultHash"] == self_hash(result, "resultHash") and config["resolutionMax"] == 192 and config["frameStart"] == 1 and config["frameEnd"] == 7 and abs(config["particleRadius"] - 1.6) <= 1e-6 and config["particleNumber"] == 2 and config["meshParticleRadius"] == 9.0 and config["meshConcaveLower"] == 0.4 and config["meshConcaveUpper"] == 3.5 and config["cupEffectorSurfaceDistanceCells"] == 2.5 and config["retainedDataManifestHash"] == retained_data["manifestHash"], checks)
    authority = result["authority"]
    check("authorityExact", authority == {"retainedDataCopied": True, "sceneStateReconstructed": True, "cacheDirectoryRebound": True, "initialUseFlipParticles": True, "initialParticleSystemCount": 1, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    thresholds = spec["acceptanceThresholds"]; metrics = result["metrics"]
    scientific = metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"] and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"] and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"] and metrics["maximumNonManifoldEdgeCount"] == 0 and signed_topology_passes(result, thresholds)
    check("scientificVerdictRecomputed", receipt["status"] == ("PASS_FINAL_EFFECTOR_MESH_STATIC" if scientific else "FAIL_FINAL_EFFECTOR_MESH_STATIC") and receipt["slowTipUnlocked"] == scientific and receipt["signedTopologyPass"] == signed_topology_passes(result, thresholds), checks)
    check("receiptSelfHashAndCounts", receipt["receiptHash"] == self_hash(receipt, "receiptHash") and receipt["counts"] == {"blenderStarts": 1, "fluidDataBakes": 0, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    check("noSymlinksOrMedia", not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")) and not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("manifestsExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK) and read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)
    committed = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{admission['researchCommit']}:{relative}"], cwd=RESEARCH, capture_output=True, check=False); committed = committed and shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed, checks)
    audit = {"schemaVersion": "bfs.rc6LiquidFinalEffectorMeshIndependentAudit.v0.1", "status": "PASS" if all(checks.values()) else "FAIL", "scientificVerdict": receipt["status"], "checks": checks, "checksPassed": sum(checks.values()), "checksTotal": len(checks), "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"], "claimCeiling": spec["claimCeiling"]}; audit["auditHash"] = self_hash(audit, "auditHash")
    with audit_path.open("x") as handle: json.dump(audit, handle, indent=2, sort_keys=True); handle.write("\n")
    print(canonical({"status": audit["status"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "scientificVerdict": audit["scientificVerdict"], "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS": raise RuntimeError("Final effector Mesh independent audit failed")


if __name__ == "__main__": main()
