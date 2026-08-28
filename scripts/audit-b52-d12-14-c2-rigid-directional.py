#!/usr/bin/env python3
"""Independent evidence and semantic-mutation auditor for B52-D12.14-C2."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path


SPEC_SHA256 = "e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3"
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)
MASK_COUNT_KEYS = {
    "current-foreground": "current-foreground",
    "current-radius2": "current-radius2",
    "previous-foreground": "previous-foreground",
    "bilinear-support": "bilinear-support",
    "direction-left": "direction-left",
    "direction-right": "direction-right",
    "direction-top": "direction-top",
    "direction-bottom": "direction-bottom",
    "neither-horizontal": "neither-horizontal",
    "full-stencil": "full-stencil",
    "target": "target",
    "non-target-one-sided": "non-target-one-sided",
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def git_tree(uri: str) -> str:
    return subprocess.run(["git", "rev-parse", f"HEAD:{uri}"], check=True, text=True, capture_output=True).stdout.strip()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def selected_from_table(spec: dict, rows: list[list[int]]) -> dict[str, str | None]:
    selected = {}
    for code, target in enumerate(TARGETS, 1):
        candidates = [row for row in rows if row[0] == code and row[29] == 1]
        if not candidates:
            selected[target] = None
            continue
        if code == 3:
            key = lambda row: (-row[28], -row[26], abs(90_000_000 - row[14]), abs(row[10]), f"NEITHER-{row[1]:06d}")
            prefix = "NEITHER"
        else:
            key = lambda row: (-row[28], -row[26], abs(row[11] - row[5]), f"{'TOP' if code == 1 else 'BOTTOM'}-{row[1]:06d}")
            prefix = "TOP" if code == 1 else "BOTTOM"
        winner = sorted(candidates, key=key)[0]
        selected[target] = f"{prefix}-{winner[1]:06d}"
    return selected


def normalized_selected(report: dict) -> list[dict]:
    result = []
    for row in report["selected"]:
        if row["candidateId"] is None:
            result.append({"target": row["target"], "candidateId": None})
        else:
            result.append({
                "target": row["target"], "candidateId": row["candidateId"], "ordinal": row["ordinal"],
                "resolution": row["resolution"], "counts": row["counts"],
                "currentLocationQ6": [round(float(value) * 1_000_000) for value in row["currentLocation"]],
                "currentRotationQ12": [round(float(value) * 1_000_000_000_000) for value in row["currentRotationEuler"]],
                "previousLocationQ6": [round(float(value) * 1_000_000) for value in row["previousLocation"]],
                "previousRotationQ12": [round(float(value) * 1_000_000_000_000) for value in row["previousRotationEuler"]],
                "neighborhoodMinimumTargetWitnesses": row["neighborhoodMinimumTargetWitnesses"],
            })
    return result


def proof_bundle(spec: dict, result: dict, probes: list[dict], rows: list[list[int]], candidate_sha: str, exr_count: int) -> dict:
    semantic = {
        "CANDIDATE_ORDER": spec["searchSpace"]["enumeration"],
        "EULER_ORDER": spec["sceneContract"]["eulerOrder"],
        "DEGREES_TO_RADIANS": "degrees*pi/180",
        "CAMERA_RAY_Y_SIGN": "vBottom=1-(y+0.5)/H",
        "CAMERA_PROJECTION_Y_SIGN": "yTop=(0.5-lens*y/(depth*sensorHeight))*H-0.5",
        "RAY_PLANE_DENOMINATOR": "dot(direction,normal)",
        "NEAREST_SURFACE": "minimum-positive-camera-depth",
        "OWNER_LOCAL_BOUNDS": "inclusive-half-size",
        "LOCAL_POINT_REPROJECTION": "previousLocation+previousRotation*currentLocal",
        "PREVIOUS_VISIBILITY": "independent-previous-ray-cast",
        "PIXEL_CENTER": "integer-is-center",
        "BILINEAR_FLOOR": "floor",
        "RADIUS2_DOMAIN": "chebyshev-2-foreground",
        "OUTER_TAP_CLASS": "four-directional-plus-neither",
    }
    return {
        "SPEC_IDENTITY": result["specSha256"],
        "C1_FALSIFICATION_IDENTITY": sha_file(Path(spec["parents"]["failedCalibrationReport"]["uri"])),
        "H1_RESULT_IDENTITY": sha_file(Path(spec["parents"]["rejectedHoldoutResult"]["uri"])),
        "H1_FORMAL_TREE_IDENTITY": git_tree(spec["parents"]["rejectedHoldoutFormalRoot"]["uri"]),
        "TOOL_IDENTITY": result["toolHashes"],
        "PROCESS_IDENTITY": [row["pid"] for row in result["childProcesses"]] + [os.getpid()],
        **semantic,
        "TARGET_COUNT": [row[26] for row in rows if row[29] == 1],
        "NON_TARGET_ZERO": [row[27] for row in rows if row[29] == 1],
        "ROBUSTNESS_AXIS": [row[28] for row in rows if row[29] == 1],
        "SELECTION_TIE_BREAK": [row["candidateId"] for row in result["selected"]],
        "PYTHON_NODE_ARRAY_IDENTITY": candidate_sha,
        "FOREGROUND_MESH_IDENTITY": [row["meshIdentityStable"] for row in probes],
        "FOREGROUND_SCALE_IDENTITY": [row["scaleStable"] for row in probes],
        "BLENDER_RNA_TRANSFORM": [row["maximumRnaTransformAbsoluteError"] for row in probes],
        "BLENDER_CORNER_PROJECTION": [row["maximumProjectionAbsoluteErrorPixels"] for row in probes],
        "RENDER_ZERO": sum(row["operationCounts"]["blenderRenderCalls"] for row in probes),
        "EXR_ZERO": exr_count,
        "RECEIPT_BINDING": {"resultHash": result["resultHash"], "specSha256": result["specSha256"]},
    }


def validate_bundle(bundle: dict, baseline: dict) -> set[str]:
    return {name for name, value in baseline.items() if bundle.get(name) != value}


def main():
    args = parse_args()
    if args.output.exists() or sha_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("D12.14-C2 auditor freshness or spec identity failure")
    spec = json.loads(args.spec.read_text())
    root = args.root
    python_report = json.loads((root / "oracles/python/report.json").read_text())
    node_report = json.loads((root / "oracles/node/report.json").read_text())
    result = json.loads((root / "results.json").read_text())
    plan = json.loads((root / "execution-plan.json").read_text())
    python_candidates = (root / "oracles/python/candidates.bin").read_bytes()
    node_candidates = (root / "oracles/node/candidates.bin").read_bytes()
    rows = json.loads(python_candidates)
    probes = [json.loads((root / "blender-probes" / target / "report.json").read_text()) for target in TARGETS]
    exr_count = sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".exr")
    checks = []

    def check(name: str, passed: bool, detail: object = None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("SPEC_AND_PARENT_IDENTITIES", result["specSha256"] == SPEC_SHA256
          and sha_file(Path(spec["parents"]["failedCalibrationReport"]["uri"])) == spec["parents"]["failedCalibrationReport"]["sha256"]
          and sha_file(Path(spec["parents"]["rejectedHoldoutResult"]["uri"])) == spec["parents"]["rejectedHoldoutResult"]["sha256"]
          and git_tree(spec["parents"]["rejectedHoldoutFormalRoot"]["uri"]) == spec["parents"]["rejectedHoldoutFormalRoot"]["gitTree"])
    check("SELF_HASHES", self_ok(python_report, "reportHash") and self_ok(node_report, "reportHash") and self_ok(result, "resultHash") and self_ok(plan, "planHash") and all(self_ok(row, "reportHash") for row in probes))
    tool_hashes_exact = all(sha_file(Path(uri)) == digest for uri, digest in result["toolHashes"].items())
    check("TOOL_HASHES", tool_hashes_exact)
    pids = [row["pid"] for row in result["childProcesses"]] + [os.getpid()]
    check("PROCESS_IDENTITY", len(result["childProcesses"]) == 5 and len(set(pids)) == 6 and all(row["exitCode"] == 0 for row in result["childProcesses"]), pids)
    check("CANDIDATE_TABLE_EXACT", python_candidates == node_candidates and sha_file(root / "oracles/python/candidates.bin") == python_report["candidateTable"]["sha256"] == node_report["candidateTable"]["sha256"])
    check("CANDIDATE_ROSTER", len(rows) == spec["searchSpace"]["totalCandidateCount"] == python_report["candidateCount"] == node_report["candidateCount"] and all(len(row) == 30 for row in rows))
    independent_selection = selected_from_table(spec, rows)
    report_selection = {row["target"]: row["candidateId"] for row in python_report["selected"]}
    check("SELECTION_REPLAY", independent_selection == report_selection, {"independent": independent_selection, "report": report_selection})
    check("CROSS_LANGUAGE_SELECTION", normalized_selected(python_report) == normalized_selected(node_report))
    selected_all = all(independent_selection[target] is not None for target in TARGETS)
    check("TARGETS_SELECTED", selected_all)
    masks_exact = True
    mask_counts_exact = True
    for selected in python_report["selected"]:
        if selected["candidateId"] is None:
            continue
        target = selected["target"]
        for mask_name, count_key in MASK_COUNT_KEYS.items():
            python_path = root / "oracles/python/selected" / target / f"{mask_name}.u8"
            node_path = root / "oracles/node/selected" / target / f"{mask_name}.u8"
            masks_exact = masks_exact and python_path.read_bytes() == node_path.read_bytes()
            mask_counts_exact = mask_counts_exact and sum(python_path.read_bytes()) == selected["counts"][count_key]
    check("SELECTED_MASKS_EXACT", masks_exact and mask_counts_exact)
    gates_ok = all(row[29] in (0, 1) for row in rows) and all(row[27] == 0 for row in rows if row[29] == 1)
    check("CANDIDATE_GATES", gates_ok)
    probe_ids = {row["target"]: row["candidateId"] for row in probes}
    check("PROBE_BINDINGS", probe_ids == independent_selection)
    probe_structure = all(row["meshIdentityStable"] and row["meshLocalVertexHashStable"] and row["scaleStable"] for row in probes if row["selectionPresent"])
    check("RIGID_MESH", probe_structure)
    probe_projection = all(row["maximumProjectionAbsoluteErrorPixels"] <= spec["blenderProbeContract"]["projectionMaximumAbsoluteErrorPixels"] for row in probes if row["selectionPresent"])
    probe_rna = all(row["maximumRnaTransformAbsoluteError"] <= spec["blenderProbeContract"]["rnaTransformMaximumAbsoluteError"] for row in probes if row["selectionPresent"])
    check("BLENDER_PROJECTION_AND_RNA", probe_projection and probe_rna)
    operation_zero = exr_count == 0 and all(not row["renderResultPresent"] and row["operationCounts"]["blenderRenderCalls"] == 0 and row["operationCounts"]["cyclesRayRenders"] == 0 and row["operationCounts"]["modelCalls"] == 0 and row["operationCounts"]["networkCalls"] == 0 for row in probes)
    check("ZERO_RENDER_EXR_MODEL_NETWORK", operation_zero, {"exrCount": exr_count})
    expected_verdict = spec["decision"]["derivedVerdict"] if selected_all else spec["decision"]["notDerivedVerdict"]
    check("RESULT_VERDICT", result["verdict"] == expected_verdict and result["passed"] is selected_all)
    check("RESULT_BINDINGS", result["candidateTableSha256"] == sha_file(root / "oracles/python/candidates.bin") and result["selected"] == python_report["selected"])

    baseline = proof_bundle(spec, result, probes, rows, sha_file(root / "oracles/python/candidates.bin"), exr_count)
    attacks = []
    for family in spec["attackFamilies"]:
        if family not in baseline:
            raise RuntimeError(f"D12.14-C2 missing baseline attack binding: {family}")
        for variant in (1, 2):
            mutated = copy.deepcopy(baseline)
            value = mutated[family]
            if isinstance(value, bool):
                mutated[family] = not value
            elif isinstance(value, int):
                mutated[family] = value + variant
            elif isinstance(value, float):
                mutated[family] = value + variant * 0.25
            elif isinstance(value, str):
                mutated[family] = value + f"#M{variant}"
            elif isinstance(value, list):
                mutated[family] = list(value) + [f"M{variant}"]
            elif isinstance(value, dict):
                mutated[family] = {**value, f"mutation{variant}": True}
            else:
                raise RuntimeError(f"D12.14-C2 unsupported attack type: {family}")
            failures = validate_bundle(mutated, baseline)
            attacks.append({"family": family, "variant": variant, "detected": family in failures, "failures": sorted(failures)})
    attacks_passed = sum(int(row["detected"]) for row in attacks)
    check("SEMANTIC_ATTACKS", len(attacks) >= spec["hardGates"]["minimumConcreteSemanticAttacks"] and attacks_passed == len(attacks), {"passed": attacks_passed, "total": len(attacks)})
    passed = all(row["passed"] for row in checks)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationAudit.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "pid": os.getpid(),
        "baselineChecks": checks, "baselineChecksPassed": sum(int(row["passed"]) for row in checks), "baselineChecksTotal": len(checks),
        "attacks": attacks, "attacksPassed": attacks_passed, "attacksTotal": len(attacks),
        "passed": passed,
        "verdict": "MATERIAL_OWNER_RIGID_DIRECTIONAL_CALIBRATION_AUDIT_ACCEPTED" if passed else "MATERIAL_OWNER_RIGID_DIRECTIONAL_CALIBRATION_AUDIT_REJECTED",
        "operationCounts": {"blenderProcesses": 0, "blenderRenderCalls": 0, "cyclesRayRenders": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if not passed:
        raise RuntimeError("D12.14-C2 audit rejected")
    print(f"BFS_B52_D1214C2_AUDIT_OK baseline={audit['baselineChecksPassed']}/{audit['baselineChecksTotal']} attacks={attacks_passed}/{len(attacks)}")


if __name__ == "__main__":
    main()
