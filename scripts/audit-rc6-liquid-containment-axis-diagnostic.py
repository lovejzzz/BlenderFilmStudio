#!/usr/bin/env python3
"""Independently audit the zero-bake liquid containment-axis diagnosis."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
SOURCE_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-mesh-concavity-attempt-31")
SOURCE_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-mesh-concavity-attempt-31"
SOURCE_CANDIDATE = SOURCE_WORK / "concavity-upper-3p50"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-01-containment-axis-attempt-32")
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-containment-axis-attempt-32"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
SCENE_TOOL = RESEARCH / "scripts/inspect-rc6-liquid-containment-axis-scene.py"
RUNNER = RESEARCH / "scripts/run-rc6-liquid-containment-axis-diagnostic.py"
AUDITOR = Path(__file__).resolve()
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-containment-axis.v0.32.json"
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


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_entries(root):
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()
    ]


def manifest(root, exclusions=()):
    excluded = set(exclusions)
    files = [entry for entry in file_entries(root) if entry["path"] not in excluded]
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": files}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def expected_argv(candidate_manifest_hash):
    return [
        str(BINARY), "--background", "--factory-startup", "--disable-autoexec", "--offline-mode",
        str(WORK / "axis-control/mesh-reconstructed-state.blend"), "--python", str(SCENE_TOOL), "--",
        "--work-root", str(WORK), "--evidence-root", str(EVIDENCE),
        "--retained-candidate-manifest-hash", candidate_manifest_hash,
    ]


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    audit_path = EVIDENCE / "independent-audit.json"
    if audit_path.exists():
        raise RuntimeError("containment-axis independent audit path is not fresh")
    spec = read_json(SPEC)
    admission = read_json(EVIDENCE / "admission.json")
    process = read_json(EVIDENCE / "processes/01-axis-control.json")
    result = read_json(EVIDENCE / "cells/axis-control/result.json")
    receipt = read_json(EVIDENCE / "receipt.json")
    source_work_manifest = read_json(SOURCE_EVIDENCE / "work-manifest.json")
    source_candidate_manifest = manifest(SOURCE_CANDIDATE)
    copied_candidate = WORK / "axis-control"
    stdout_path = EVIDENCE / "logs/01-axis-control.stdout.log"
    stderr_path = EVIDENCE / "logs/01-axis-control.stderr.log"
    checks = {}

    check("specSelfHash", spec.get("status") == "FROZEN" and spec.get("specHash") == self_hash(spec, "specHash"), checks)
    check("toolRosterExact", spec.get("tools") == {
        str(SCENE_TOOL.relative_to(RESEARCH)): sha(SCENE_TOOL),
        str(RUNNER.relative_to(RESEARCH)): sha(RUNNER),
        str(AUDITOR.relative_to(RESEARCH)): sha(AUDITOR),
    }, checks)
    check("rootsExact", spec["roots"] == {
        "sourceWork": str(SOURCE_WORK), "sourceEvidence": str(SOURCE_EVIDENCE),
        "sourceCandidate": str(SOURCE_CANDIDATE), "work": str(WORK), "evidence": str(EVIDENCE),
    }, checks)
    check("binaryExact", sha(BINARY) == spec["inputs"]["binarySha256"] == admission["binarySha256"], checks)
    check("sourceWorkExact", source_work_manifest == manifest(SOURCE_WORK) and sha(SOURCE_EVIDENCE / "work-manifest.json") == spec["inputs"]["sourceWorkManifestFileSha256"], checks)
    check("sourceCandidateExact", source_candidate_manifest["manifestHash"] == spec["inputs"]["sourceCandidateManifestHash"] and read_json(EVIDENCE / "retained-candidate-manifest.json") == source_candidate_manifest, checks)
    check("copiedCandidateExact", file_entries(copied_candidate) == source_candidate_manifest["files"], checks)
    check("admissionSelfHash", admission.get("status") == "PASS" and admission.get("admissionHash") == self_hash(admission, "admissionHash"), checks)
    check("processSelfHash", process.get("processHash") == self_hash(process, "processHash"), checks)
    check("argvExact", process.get("argv") == expected_argv(source_candidate_manifest["manifestHash"]) and process.get("cwd") == str(RESEARCH), checks)
    check("processAndLogs", process.get("exitCode") == 0 and sha(stdout_path) == process.get("stdoutSha256") and sha(stderr_path) == process.get("stderrSha256") and stderr_path.stat().st_size == 0 and "RC6_CONTAINMENT_AXIS=" in stdout_path.read_text(encoding="utf-8", errors="replace"), checks)
    check("resultSelfHash", result.get("status") == "MEASURED_READ_ONLY" and result.get("resultHash") == self_hash(result, "resultHash") and receipt.get("resultHash") == result.get("resultHash"), checks)
    check("configurationExact", result.get("configuration") == {
        "frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "baseVoxelMeters": 0.0026041667,
        "radialLimitCupLocalMeters": 0.0926041667, "bottomLimitCupLocalMeters": -0.1626041667, "topLimitCupLocalMeters": 0.2226041667,
        "particleRadius": 1.6, "meshParticleRadius": 9.0, "meshConcaveLower": 0.4, "meshConcaveUpper": 3.5,
        "meshSmoothenPos": 1, "meshSmoothenNeg": 1,
        "cupRawMeshRadialZHistogram": {
            "0.00000000@-0.22000000": 1, "0.00000000@-0.16000000": 1,
            "0.09000000@-0.16000000": 64, "0.09000000@0.22000000": 64,
            "0.15000000@-0.22000000": 64, "0.15000000@0.22000000": 64,
        },
        "cupEffectorSurfaceDistance": 0.0015,
    }, checks)
    check("authorityExact", result.get("authority") == {
        "copiedCandidateReadOnly": True, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0,
        "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0,
    }, checks)
    check("sevenSamples", [row.get("frame") for row in result.get("samples", [])] == list(range(1, 8)), checks)
    arithmetic_exact = True
    for sample in result.get("samples", []):
        for row in [sample.get("aggregate", {})] + sample.get("components", []):
            combos = row.get("exclusiveCombinations", {})
            count = row.get("vertexCount", 0)
            union = row.get("outsideUnionCount", -1)
            arithmetic_exact = arithmetic_exact and sum(combos.values()) == count and union == count - combos.get("inside", 0)
            arithmetic_exact = arithmetic_exact and row.get("radialCount") == combos.get("radialOnly", 0) + combos.get("radialAndBelow", 0) + combos.get("radialAndAbove", 0) + combos.get("allThree", 0)
            arithmetic_exact = arithmetic_exact and row.get("belowFloorCount") == combos.get("belowOnly", 0) + combos.get("radialAndBelow", 0) + combos.get("belowAndAbove", 0) + combos.get("allThree", 0)
            arithmetic_exact = arithmetic_exact and row.get("aboveRimCount") == combos.get("aboveOnly", 0) + combos.get("radialAndAbove", 0) + combos.get("belowAndAbove", 0) + combos.get("allThree", 0)
    check("axisArithmeticExact", arithmetic_exact, checks)

    peak = max(result["samples"], key=lambda row: row["aggregate"]["outsideUnionFraction"])
    peak_counts = {"radial": peak["aggregate"]["radialCount"], "belowFloor": peak["aggregate"]["belowFloorCount"], "aboveRim": peak["aggregate"]["aboveRimCount"]}
    dominant_axis = max(peak_counts, key=peak_counts.get)
    dominant_share = peak_counts[dominant_axis] / peak["aggregate"]["outsideUnionCount"] if peak["aggregate"]["outsideUnionCount"] else 0.0
    check("receiptSelfHash", receipt.get("receiptHash") == self_hash(receipt, "receiptHash") and receipt.get("status") == "PASS_EXECUTION", checks)
    check("receiptDiagnosisRecomputed", receipt.get("diagnosticVerdict") == "MEASURED_AXIS_CAUSE" and receipt.get("peakOutsideFrame") == peak["frame"] and receipt.get("peakOutsideUnionFraction") == peak["aggregate"]["outsideUnionFraction"] and receipt.get("peakAxisCounts") == peak_counts and receipt.get("dominantAxis") == dominant_axis and receipt.get("dominantAxisShareOfOutsideUnion") == round(dominant_share, 8), checks)
    check("countCeilingsExact", receipt.get("counts") == {"blenderStarts": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 0, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, checks)
    check("noSymlinksOrMedia", not any(path.is_symlink() for root in (SOURCE_WORK, WORK, EVIDENCE) for path in root.rglob("*")) and not any(path.is_file() and path.suffix.lower() in BANNED_MEDIA for root in (WORK, EVIDENCE) for path in root.rglob("*")), checks)
    ceilings = spec["resourceCeilings"]
    check("resourceCeilings", tree_bytes(WORK) <= ceilings["workBytes"] and tree_bytes(EVIDENCE) <= ceilings["evidenceBytes"] and receipt["resources"]["freeBytesAfter"] >= ceilings["minimumFreeBytesAfter"], checks)
    check("workManifestExact", read_json(EVIDENCE / "work-manifest.json") == manifest(WORK), checks)
    check("evidenceManifestExact", read_json(EVIDENCE / "evidence-manifest.json") == manifest(EVIDENCE, exclusions=("evidence-manifest.json", "independent-audit.json")), checks)
    commit = admission["researchCommit"]
    committed_exact = True
    for relative in list(spec["tools"]) + [str(SPEC.relative_to(RESEARCH))]:
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=RESEARCH, capture_output=True, check=False)
        committed_exact = committed_exact and shown.returncode == 0 and hashlib.sha256(shown.stdout).hexdigest() == sha(RESEARCH / relative)
    check("committedToolAndSpecBytesExact", committed_exact, checks)

    audit = {
        "schemaVersion": "bfs.rc6LiquidContainmentAxisIndependentAudit.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "diagnosticVerdict": receipt["diagnosticVerdict"],
        "peakOutsideFrame": peak["frame"],
        "peakAxisCounts": peak_counts,
        "dominantAxis": dominant_axis,
        "dominantAxisShareOfOutsideUnion": round(dominant_share, 8),
        "checks": checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "receiptHash": receipt["receiptHash"],
        "resultHash": result["resultHash"],
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(audit_path, audit)
    print(canonical({"status": audit["status"], "diagnosticVerdict": audit["diagnosticVerdict"], "dominantAxis": audit["dominantAxis"], "checks": f"{audit['checksPassed']}/{audit['checksTotal']}", "auditHash": audit["auditHash"]}))
    if audit["status"] != "PASS":
        raise RuntimeError("containment-axis independent audit failed")


if __name__ == "__main__":
    main()
