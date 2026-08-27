#!/usr/bin/env python3
"""Analyze B52-D6 against an independent deterministic float32 warp."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

from b52_d6_reference import (
    SPEC_SHA256,
    array_hash,
    canonical_hash,
    displacement_array,
    fixture_by_id,
    read_png,
    read_rgba,
    reference_warp,
    sha256_file,
    source_array,
    write_png,
)


EVIDENCE_FIELDS = {
    "PARENT_IDENTITY": "parentIdentity",
    "RUNTIME_BINARY_IDENTITY": "runtimeBinaryIdentity",
    "OCIO_IDENTITY": "ocioIdentity",
    "CASE_ROSTER": "caseRoster",
    "PROCESS_ROSTER": "processRoster",
    "PID_UNIQUENESS": "pidUniqueness",
    "REPORT_SELF_HASH": "reportSelfHash",
    "SOURCE_FORMULA": "sourceFormula",
    "DISPLACEMENT_FORMULA": "displacementFormula",
    "RNA_CONTRACT": "rnaContract",
    "GRAPH_CONTRACT": "graphContract",
    "OPERATION_COUNTS": "operationCounts",
    "OUTPUT_HASH": "outputHash",
    "DECODED_REPEAT": "decodedRepeat",
    "REFERENCE_ARRAY_HASH": "referenceArrayHash",
    "REFERENCE_MATCH": "referenceMatch",
    "TASK_SENSITIVITY": "taskSensitivity",
    "DIAGNOSTIC_ROSTER": "diagnosticRoster",
    "DIAGNOSTIC_SIDECAR": "diagnosticSidecar",
    "RESULT_SELF_HASH": "resultSelfHash",
}


def report_hash_valid(report: dict) -> bool:
    body = {key: value for key, value in report.items() if key != "reportHash"}
    return report.get("reportHash") == canonical_hash(body)


def first_failure(evidence: dict, spec: dict) -> str | None:
    for attack in spec["attacks"]:
        if not evidence.get(EVIDENCE_FIELDS[attack], False):
            return attack
    return None


def synthetic_valid_evidence(spec: dict) -> dict:
    return {field: True for field in EVIDENCE_FIELDS.values()}


def attack_contract(spec: dict) -> list[dict]:
    attacks = []
    for attack in spec["attacks"]:
        evidence = synthetic_valid_evidence(spec)
        evidence[EVIDENCE_FIELDS[attack]] = False
        observed = first_failure(evidence, spec)
        attacks.append({"attack": attack, "expectedFailure": attack, "observedFailure": observed, "passed": observed == attack})
    return attacks


def encode_reference(reference: np.ndarray) -> np.ndarray:
    return np.floor(np.clip(reference[..., :3], 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def encode_error(error: np.ndarray) -> np.ndarray:
    threshold = 1.0 / 65536.0
    maximum = np.max(error, axis=2)
    t = np.clip(maximum / threshold, 0.0, 1.0)
    mapped = np.stack((t, t * t, np.zeros_like(t)), axis=2)
    return np.floor(mapped * 255.0 + 0.5).astype(np.uint8)


def write_diagnostic(root: Path, canonical_root: str, fixture_id: str, kind: str, encoded: np.ndarray, sources: dict) -> dict:
    slug = fixture_id.lower().replace("_", "-")
    png_path = root / f"{slug}-{kind}.png"
    sidecar_path = root / f"{slug}-{kind}.json"
    write_png(png_path, encoded)
    decoded = read_png(png_path)
    decoded_hash = canonical_hash({"shape": list(decoded.shape), "bytesSha256": __import__("hashlib").sha256(decoded.tobytes()).hexdigest()})
    expected_hash = canonical_hash({"shape": list(encoded.shape), "bytesSha256": __import__("hashlib").sha256(encoded.tobytes()).hexdigest()})
    identity_match = np.array_equal(decoded, encoded) and decoded_hash == expected_hash
    png_binding = {
        "uri": f"{canonical_root}/{png_path.name}",
        "sha256": sha256_file(png_path),
        "bytes": png_path.stat().st_size,
        "decodedSha256": decoded_hash,
    }
    sidecar_body = {
        "schemaVersion": "bfs.deterministicDisplaceDiagnostic.v0.1",
        "fixtureId": fixture_id,
        "kind": kind,
        "encoding": "REFERENCE_RGB_LINEAR" if kind == "reference" else "MAX_RGBA_ERROR_OVER_1_OVER_65536",
        "sources": sources,
        "png": png_binding,
        "decodedIdentityMatch": identity_match,
    }
    sidecar_path.write_text(json.dumps(sidecar_body, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return {
        "fixtureId": fixture_id,
        "kind": kind,
        "png": png_binding,
        "sidecar": {"uri": f"{canonical_root}/{sidecar_path.name}", "sha256": sha256_file(sidecar_path), "bytes": sidecar_path.stat().st_size},
        "identityMatch": identity_match,
    }


def analyze(spec: dict, receipt: dict, output_path: Path, receipt_sha256: str, root: Path) -> dict:
    canonical_root = spec["formalOutputRoot"]
    diagnostics_root = output_path.parent / "diagnostics"
    references_root = output_path.parent / "references"
    diagnostics_root.mkdir(parents=True, exist_ok=False)
    references_root.mkdir(parents=True, exist_ok=False)
    source = source_array(spec)
    source_hash = array_hash(source)
    runs = receipt.get("runs", [])
    expected_pairs = {(fixture["id"], repeat) for fixture in spec["fixtures"] for repeat in (1, 2)}
    actual_pairs = {(run.get("fixtureId"), run.get("repeat")) for run in runs}
    reports = [run.get("report") for run in runs]
    report_bodies = [report for report in reports if isinstance(report, dict)]
    pids = [run.get("pid") for run in runs]

    measurements = []
    diagnostics = []
    output_hash_checks = []
    report_hash_checks = []
    rna_checks = []
    graph_checks = []
    source_formula_checks = []
    displacement_formula_checks = []
    finite_checks = []
    repeat_checks = []
    reference_checks = []
    reference_artifact_checks = []
    sensitivity_checks = []

    for fixture_spec in spec["fixtures"]:
        fixture_id = fixture_spec["id"]
        displacement = displacement_array(spec, fixture_id)
        displacement_hash = array_hash(displacement)
        reference = reference_warp(source, displacement, fixture_spec)
        reference_hash = array_hash(reference)
        reference_path = references_root / f"{fixture_id.lower().replace('_', '-')}.rgba32"
        reference_path.write_bytes(np.ascontiguousarray(reference, dtype="<f4").tobytes(order="C"))
        reference_binding = {
            "uri": f"{canonical_root}/references/{reference_path.name}",
            "sha256": sha256_file(reference_path),
            "bytes": reference_path.stat().st_size,
            "decodedFloat32Sha256": reference_hash,
        }
        reference_artifact_checks.append(reference_binding["sha256"] == reference_hash)
        fixture_runs = sorted([run for run in runs if run.get("fixtureId") == fixture_id], key=lambda item: item.get("repeat", 0))
        decoded = []
        run_bindings = []
        for run in fixture_runs:
            report = run.get("report")
            report_ok = isinstance(report, dict) and report_hash_valid(report)
            report_hash_checks.append(report_ok)
            output = report.get("output") if isinstance(report, dict) else None
            output_path_actual = root / output["uri"] if isinstance(output, dict) and output.get("uri") else None
            output_ok = output_path_actual is not None and output_path_actual.is_file() and sha256_file(output_path_actual) == output.get("sha256") and output_path_actual.stat().st_size == output.get("bytes")
            output_hash_checks.append(output_ok)
            pixels = read_rgba(output_path_actual) if output_ok else np.full_like(source, np.nan)
            decoded.append(pixels)
            finite_checks.append(bool(np.isfinite(pixels).all()))
            rna_checks.append(bool(report and report.get("rna", {}).get("match")))
            graph_checks.append(bool(report and report.get("graph", {}).get("match")))
            source_formula_checks.append(bool(report and report.get("arrays", {}).get("sourceFloat32Sha256") == source_hash))
            displacement_formula_checks.append(bool(report and report.get("arrays", {}).get("displacementFloat32Sha256") == displacement_hash))
            run_bindings.append({"repeat": run.get("repeat"), "pid": run.get("pid"), "reportUri": run.get("reportUri"), "output": output, "decodedFloat32Sha256": array_hash(pixels) if np.isfinite(pixels).all() else None})
        repeat_exact = len(decoded) == 2 and np.array_equal(decoded[0], decoded[1])
        repeat_checks.append(repeat_exact)
        observed = decoded[0] if decoded else np.full_like(reference, np.nan)
        error = np.abs(observed.astype(np.float64) - reference.astype(np.float64))
        maximum_error = float(np.max(error)) if np.isfinite(error).all() else math.inf
        rmse = float(np.sqrt(np.mean(np.square(error)))) if np.isfinite(error).all() else math.inf
        pixels_above = int(np.count_nonzero(np.max(error, axis=2) > 1.0 / 65536.0)) if np.isfinite(error).all() else source.shape[0] * source.shape[1]
        observed_hash = array_hash(observed) if np.isfinite(observed).all() else None
        reference_match = observed_hash == reference_hash and maximum_error == 0.0 and rmse == 0.0 and pixels_above == 0
        reference_checks.append(reference_match)
        change = np.abs(reference.astype(np.float64) - source.astype(np.float64))
        changed_pixels = int(np.count_nonzero(np.max(change, axis=2) > 1.0 / 65536.0))
        maximum_change = float(np.max(change))
        sensitivity_pass = (not fixture_spec["sensitivityRequired"] and reference_hash == source_hash) or (
            fixture_spec["sensitivityRequired"]
            and changed_pixels >= spec["gates"]["minimumChangedPixelsAboveOneOver65536ForSensitiveFixture"]
            and maximum_change >= spec["gates"]["minimumMaximumAbsoluteChangeForSensitiveFixture"]
        )
        sensitivity_checks.append(sensitivity_pass)
        sources = {
            "sourceFloat32Sha256": source_hash,
            "displacementFloat32Sha256": displacement_hash,
            "referenceFloat32Sha256": reference_hash,
            "renderedFloat32Sha256": observed_hash,
        }
        diagnostics.append(write_diagnostic(diagnostics_root, f"{canonical_root}/diagnostics", fixture_id, "reference", encode_reference(reference), sources))
        diagnostics.append(write_diagnostic(diagnostics_root, f"{canonical_root}/diagnostics", fixture_id, "error", encode_error(error), sources))
        measurements.append({
            "fixtureId": fixture_id,
            "sampling": {"interpolation": fixture_spec["interpolation"], "extensionX": fixture_spec["extensionX"], "extensionY": fixture_spec["extensionY"]},
            "sourceFloat32Sha256": source_hash,
            "displacementFloat32Sha256": displacement_hash,
            "reference": reference_binding,
            "runs": run_bindings,
            "repeatExact": repeat_exact,
            "observedFloat32Sha256": observed_hash,
            "referenceMatch": reference_match,
            "maximumAbsoluteError": maximum_error,
            "rmse": rmse,
            "pixelsAboveOneOver65536": pixels_above,
            "changedPixelsAboveOneOver65536": changed_pixels,
            "maximumAbsoluteChange": maximum_change,
            "sensitivityPass": sensitivity_pass,
        })

    operation_counts = {
        "blenderProcesses": len(runs),
        "renderCalls": sum((report or {}).get("operationCounts", {}).get("renderCalls", 0) for report in report_bodies),
        "cyclesRayRenders": sum((report or {}).get("operationCounts", {}).get("cyclesRayRenders", 0) for report in report_bodies),
        "sourceBlendFilesOpened": sum((report or {}).get("operationCounts", {}).get("sourceBlendFilesOpened", 0) for report in report_bodies),
        "externalAssetsOpened": sum((report or {}).get("operationCounts", {}).get("externalAssetsOpened", 0) for report in report_bodies),
    }
    expected_counts = {
        "blenderProcesses": spec["blenderMatrix"]["expectedProcesses"],
        "renderCalls": spec["blenderMatrix"]["expectedRenderCalls"],
        "cyclesRayRenders": spec["blenderMatrix"]["expectedCyclesRayRenders"],
        "sourceBlendFilesOpened": spec["blenderMatrix"]["sourceBlendFilesOpened"],
        "externalAssetsOpened": spec["blenderMatrix"]["externalAssetsOpened"],
    }
    evidence = {
        "parentIdentity": bool(receipt.get("checks", {}).get("parentIdentity")),
        "runtimeBinaryIdentity": bool(receipt.get("checks", {}).get("runtimeBinaryIdentity")),
        "ocioIdentity": bool(receipt.get("checks", {}).get("ocioIdentity")),
        "caseRoster": actual_pairs == expected_pairs,
        "processRoster": len(runs) == spec["blenderMatrix"]["expectedProcesses"] and all(run.get("exitCode") == 0 and not run.get("timedOut") and isinstance(run.get("report"), dict) for run in runs),
        "pidUniqueness": len(pids) == len(set(pids)) == spec["blenderMatrix"]["expectedProcesses"],
        "reportSelfHash": len(report_hash_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(report_hash_checks),
        "sourceFormula": len(source_formula_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(source_formula_checks),
        "displacementFormula": len(displacement_formula_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(displacement_formula_checks),
        "rnaContract": len(rna_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(rna_checks),
        "graphContract": len(graph_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(graph_checks),
        "operationCounts": operation_counts == expected_counts,
        "outputHash": len(output_hash_checks) == spec["blenderMatrix"]["expectedProcesses"] and all(output_hash_checks),
        "decodedRepeat": len(repeat_checks) == len(spec["fixtures"]) and all(repeat_checks),
        "referenceArrayHash": len(reference_artifact_checks) == len(spec["fixtures"]) and all(reference_artifact_checks),
        "referenceMatch": len(reference_checks) == len(spec["fixtures"]) and all(reference_checks),
        "taskSensitivity": len(sensitivity_checks) == len(spec["fixtures"]) and all(sensitivity_checks),
        "diagnosticRoster": len(diagnostics) == spec["diagnostics"]["expectedPngs"],
        "diagnosticSidecar": len(diagnostics) == spec["diagnostics"]["expectedSidecars"] and all(item["identityMatch"] for item in diagnostics),
        "resultSelfHash": True,
    }
    attacks = attack_contract(spec)
    if len(attacks) != len(spec["attacks"]) or not all(item["passed"] for item in attacks):
        raise RuntimeError("B52-D6 attack contract does not route all frozen attacks")
    base_failure = first_failure(evidence, spec)
    verdict = spec["decision"]["passVerdict"] if base_failure is None else spec["decision"]["failVerdict"]
    core = {"evidence": evidence, "measurements": measurements, "operationCounts": operation_counts, "verdict": verdict, "baseFailure": base_failure}
    body = {
        "schemaVersion": "bfs.deterministicDisplaceCalibrationResult.v0.1",
        "experimentId": spec["experimentId"],
        "preregistration": receipt["preregistration"],
        "toolFreezeCommit": receipt["toolFreezeCommit"],
        "receipt": {"uri": f"{canonical_root}/run.receipt.json", "sha256": receipt_sha256},
        "evidence": evidence,
        "measurements": measurements,
        "diagnostics": diagnostics,
        "operationCounts": operation_counts,
        "attacks": attacks,
        "attacksPassed": sum(item["passed"] for item in attacks),
        "evidenceCoreHash": canonical_hash(core),
        "verdict": verdict,
        "baseFailure": base_failure,
        "nonClaims": spec["decision"]["nonClaims"],
    }
    return {**body, "resultHash": canonical_hash(body)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B52-D6 spec hash mismatch")
    if args.output.exists() or args.output.parent.joinpath("diagnostics").exists() or args.output.parent.joinpath("references").exists():
        raise RuntimeError("refusing to overwrite B52-D6 analysis output")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    root = args.spec.resolve().parent.parent
    result = analyze(spec, receipt, args.output, sha256_file(args.receipt), root)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D6_ANALYSIS {result['verdict']} baseFailure={result['baseFailure']} attacks={result['attacksPassed']}/{len(spec['attacks'])}", flush=True)


if __name__ == "__main__":
    main()
