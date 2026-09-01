#!/usr/bin/env python3
"""Independently audit the resolution-192 35 mm static confirmation."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-source-clearance-final-attempt-25")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-source-clearance-final-attempt-25"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SOURCE_BLEND = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-feasibility-attempt-13/RC6_F1_BULLET_MANTAFLOW_CONSEQUENCE.blend")
SCENE_TOOL = RESEARCH / "scripts/run-rc6-liquid-source-clearance-final-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-source-clearance-final.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-source-clearance-final.v0.25.json"
CELL_ID = "clearance-35mm-res192"
BANNED_MEDIA = {".exr", ".png", ".jpg", ".jpeg", ".mov", ".mp4"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha(value):
    return hashlib.sha256(value).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if relative in excluded:
            continue
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def expected_argv():
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(SOURCE_BLEND), "--python", str(SCENE_TOOL), "--", "--cell-id", CELL_ID,
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE), "--resolution", "192",
        "--frame-end", "7", "--particle-radius", "1.6", "--particle-number", "2",
        "--mesh-particle-radius", "4.5", "--source-bottom-clearance", "0.035",
    ]


def expected_cache_files():
    return sorted(
        [f"config/config_{frame:04d}.uni" for frame in range(1, 8)]
        + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)]
        + [f"mesh/fluid_mesh_{frame:04d}.bobj.gz" for frame in range(1, 8)]
    )


def signed_topology_passes(result, thresholds):
    for sample in result["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"] or any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            contained = all(inner["boundsMinWorld"][axis] >= outer["boundsMinWorld"][axis] - 1e-7 and inner["boundsMaxWorld"][axis] <= outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3))
            separation = sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5
            if not contained or separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("final static independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    process = read_json(EVIDENCE / "processes/01-final-static.json")
    result = read_json(EVIDENCE / "cells" / CELL_ID / "result.json")
    receipt = read_json(EVIDENCE / "receipt.json")
    stdout_path = EVIDENCE / "logs/01-final-static.stdout.log"
    stderr_path = EVIDENCE / "logs/01-final-static.stderr.log"
    checks = {}
    check("specSelfHash", spec.get("specHash") == self_hash(spec, "specHash") and spec.get("status") == "FROZEN", checks)
    check("toolRosterExact", spec.get("tools") == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }, checks)
    check("inputIdentities", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"] and sha(SOURCE_BLEND) == spec["inputs"]["sourceBlendSha256"] == admission["sourceBlendSha256"], checks)
    check("admissionSelfHash", admission.get("admissionHash") == self_hash(admission, "admissionHash") and admission.get("status") == "PASS", checks)
    check("processSelfHash", process.get("processHash") == self_hash(process, "processHash"), checks)
    check("argvExact", process.get("argv") == expected_argv() and process.get("cwd") == str(RESEARCH), checks)
    check("processSuccess", process.get("exitCode") == 0 and sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0, checks)
    check("resultSelfHash", result.get("resultHash") == self_hash(result, "resultHash") and result.get("status") == "MEASURED" and result.get("cellId") == CELL_ID, checks)
    configuration = dict(result["configuration"])
    measured_clearance = configuration.pop("sourceBottomClearanceMeters")
    measured_voxels = configuration.pop("sourceBottomClearanceVoxels")
    check("configurationExact", configuration == spec["configuration"], checks)
    binding = spec["measurementBinding"]
    check("placementRoundoffBound", abs(measured_clearance - binding["requestedClearanceMeters"]) <= binding["maximumAbsoluteClearanceErrorMeters"] and abs(measured_voxels - binding["requestedClearanceVoxels"]) <= binding["maximumAbsoluteClearanceErrorVoxels"], checks)
    check("sevenSamplesExact", [item.get("frame") for item in result.get("samples", [])] == list(range(1, 8)), checks)
    check("sourceVolumeExact", abs(result["metrics"]["sourceMeshVolumeCubicMeters"] - spec["inputs"]["sourceMeshVolumeCubicMeters"]) <= 1e-15, checks)
    baked = result["bakedState"]
    baked_path = Path(baked["uri"])
    check("bakedStateExact", baked_path.is_file() and baked_path.stat().st_size == baked["bytes"] and sha(baked_path) == baked["sha256"], checks)
    cache_root = baked_path.parent / "mantaflow-cache"
    actual_cache = sorted(str(path.relative_to(cache_root)) for path in cache_root.rglob("*") if path.is_file())
    check("cacheRosterExact", result.get("cacheFiles") == expected_cache_files() and actual_cache == expected_cache_files(), checks)
    thresholds = spec["acceptanceThresholds"]
    metrics = result["metrics"]
    recomputed = {
        "sourceVolumeWithinFivePercent": metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"],
        "temporalDriftWithinFivePercent": metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"],
        "containedWithinOnePercent": metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"],
        "manifold": metrics["maximumNonManifoldEdgeCount"] == thresholds["maximumNonManifoldEdgeCount"],
        "signedTopology": signed_topology_passes(result, thresholds),
        "zeroRender": result["authority"]["renderCalls"] == 0,
        "zeroNetwork": result["authority"]["networkCalls"] == 0,
    }
    ceilings = spec["resourceCeilings"]
    recomputed["resourceCeilings"] = tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and receipt["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"]
    recomputed["zeroRenderMedia"] = not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*"))
    check("scientificChecksRecomputed", receipt.get("checks") == recomputed, checks)
    expected_status = "PASS_FINAL_STATIC" if all(recomputed.values()) else "FAIL_FINAL_STATIC"
    check("verdictRecomputed", receipt.get("status") == expected_status and receipt.get("slowTipUnlocked") is all(recomputed.values()), checks)
    check("receiptSelfHash", receipt.get("receiptHash") == self_hash(receipt, "receiptHash"), checks)
    check("countCeilings", receipt.get("counts") == {"blenderStarts": 1, "fluidDataBakes": 1, "fluidMeshBakes": 1, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    check("noSymlinks", not any(path.is_symlink() for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    check("workManifestExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK), checks)
    check("evidenceManifestExact", read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)
    retained = spec["retainedStaticControl"]
    for label, item in retained.items():
        path = RESEARCH / item["path"]
        check(f"retained_{label}", path.is_file() and sha(path) == item["sha256"], checks)
    committed_exact = True
    commit = admission["researchCommit"]
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and bytes_sha(shown.stdout) == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)
    audit = {
        "schemaVersion": "bfs.rc6LiquidSourceClearanceFinalIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL", "scientificVerdict": receipt["status"],
        "slowTipUnlocked": receipt["slowTipUnlocked"], "checks": checks,
        "checksPassed": sum(checks.values()), "checksTotal": len(checks),
        "receiptHash": receipt["receiptHash"], "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "scientificVerdict": audit["scientificVerdict"], "slowTipUnlocked": audit["slowTipUnlocked"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("final static independent audit failed")


if __name__ == "__main__":
    main()
