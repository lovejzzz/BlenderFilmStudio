#!/usr/bin/env python3
"""Independent integrity and semantic replay audit for B52-D11.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import subprocess
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a"
CORRECTION_PROTOCOL = "research/2026-08-27-b52-d11-1-c1-audit-numpy-bool-correction.md"
CORRECTION_PROTOCOL_SHA256 = "074a77353b78c52633b6ecc99752ffdeec74f6eff11e8876f65ea1da5974e32b"
CORRECTION_PREREGISTRATION_COMMIT = "c81fcb8c92a4873e86a344562c20553d2284f441"
ORIGINAL_AUDIT = "scripts/audit-b52-d11-1-nearest-integer-recovery.py"
ORIGINAL_AUDIT_SHA256 = "feb1214b00b16e833db2e65f38308d4c82b76f8952aadf62ad0a72670fbabb4a"
RESULT_SHA256 = "dd08142a2af855ddc287eecb84f5de722afb03a9ae6aef8a33fd3279d660329f"
RECEIPT_SHA256 = "643717651d4dafb48c87c0527d682ea224e8ab80f6a81a8d153e8c4d1ec8a9fc5"
C1_TOOL = "scripts/audit-b52-d11-1-nearest-integer-recovery-c1.py"
ADAPTER_FILES = {"previousRgba": ("previous.rgba32", 4), "currentRgba": ("current.rgba32", 4), "previousDepth": ("previous-depth.f32", 1), "currentDepth": ("current-depth.f32", 1), "previousLayer": ("previous-layer.f32", 1), "currentLayer": ("current-layer.f32", 1), "motion": ("motion.xy32", 2)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def action_exact(rows: list[dict], values: dict[str, list[float]] | None) -> bool:
    if values is None:
        return rows == []
    if len(rows) != 3:
        return False
    ordered = sorted(((int(frame), location) for frame, location in values.items()), key=lambda item: item[0])
    for axis, row in enumerate(rows):
        if (row["layerIndex"], row["stripIndex"], row["channelBagIndex"], row["dataPath"], row["arrayIndex"]) != (0, 0, 0, "location", axis):
            return False
        if len(row["keyframes"]) != len(ordered):
            return False
        for observed, (frame, location) in zip(row["keyframes"], ordered):
            if f32(observed["frame"]) != f32(frame) or f32(observed["value"]) != f32(location[axis]) or observed["interpolation"] != "LINEAR":
                return False
    return True


def valid_hashed_json(path: Path, field: str) -> tuple[bool, dict]:
    payload = json.loads(path.read_text())
    body = {key: value for key, value in payload.items() if key != field}
    return payload.get(field) == canonical_hash(body), payload


def multipart(path: Path) -> dict[str, np.ndarray]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    result = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        result[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return result


def rgba(path: Path) -> np.ndarray:
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(oiio.geterror())
    image_spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), np.float32).reshape(image_spec.height, image_spec.width, 4)
    image.close()
    return np.ascontiguousarray(pixels, dtype="<f4")


def adapter_arrays(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    result = {}
    for name, (filename, components) in ADAPTER_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        result[name] = np.frombuffer((directory / filename).read_bytes(), dtype="<f4").reshape(shape)
    return result


def nearest_integer(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)


def quantize(raw: np.ndarray, radius: float) -> np.ndarray | None:
    output = np.empty(raw.size, dtype="<f4")
    for index, scalar in enumerate(np.ascontiguousarray(raw, dtype="<f4").reshape(-1)):
        value = float(scalar)
        if not math.isfinite(value):
            return None
        candidate = nearest_integer(value)
        if abs(value - candidate) > radius:
            return None
        output[index] = np.float32(0.0 if candidate == 0 else candidate)
    return output.reshape(raw.shape)


def replay(arrays: dict[str, np.ndarray], sign: int = 1, naive: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = arrays["currentDepth"].shape
    validity = np.zeros((height, width), np.uint8)
    reasons = np.zeros((height, width), np.uint8)
    resolved = arrays["currentRgba"].copy()
    for y in range(height):
        for x in range(width):
            dx, dy = int(float(arrays["motion"][y, x, 0])), int(float(arrays["motion"][y, x, 1]))
            qx, qy = x - sign * dx, y + sign * dy
            if not (0 <= qx < width and 0 <= qy < height):
                reason = 1
            elif naive:
                reason = 0
            elif arrays["previousLayer"][qy, qx] != arrays["currentLayer"][y, x]:
                reason = 2
            elif abs(float(arrays["previousDepth"][qy, qx]) - float(arrays["currentDepth"][y, x])) > max(1.0, float(arrays["currentDepth"][y, x])) / 1024.0:
                reason = 3
            elif arrays["previousRgba"][qy, qx, 3] <= 0 or arrays["currentRgba"][y, x, 3] <= 0:
                reason = 4
            else:
                reason = 0
            reasons[y, x] = reason
            if reason == 0:
                validity[y, x] = 1
                for channel in range(4):
                    resolved[y, x, channel] = np.float32(0.5 * float(arrays["currentRgba"][y, x, channel]) + 0.5 * float(arrays["previousRgba"][qy, qx, channel]))
    return validity, reasons, resolved


def owner_mask(spec: dict, fixture: dict) -> np.ndarray:
    width, height = spec["scene"]["resolution"]
    if "CAMERA_BOUNDS" in fixture["id"] or "STATIC" in fixture["id"]:
        return np.ones((height, width), bool)
    mover = next(item for item in fixture["objects"] if "locationByFrame" in item)
    camera = fixture.get("cameraByFrame", {}).get("1", spec["scene"]["camera"]["location"])
    location = mover["locationByFrame"]["1"]
    scale = width / float(spec["scene"]["camera"]["orthoScale"])
    xs = camera[0] + (np.arange(width) + 0.5 - width / 2.0) / scale
    ys = camera[1] + (height / 2.0 - np.arange(height) - 0.5) / scale
    margin = 1.1 / scale
    return (np.abs(ys[:, None] - location[1]) < mover["sizeWorld"][1] / 2.0 - margin) & (np.abs(xs[None, :] - location[0]) < mover["sizeWorld"][0] / 2.0 - margin)


def difference(candidate: np.ndarray, reference: np.ndarray) -> tuple[int, float]:
    delta = np.abs(candidate.astype(np.float64) - reference.astype(np.float64))
    return int(np.count_nonzero(np.any(delta != 0, axis=2))), float(delta.max(initial=0.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--correction-freeze-commit", required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if sha(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("B52-D11.1 audit identity/output mismatch")
    result_path, receipt_path = args.formal_root / "results.json", args.formal_root / "run.receipt.json"
    root = Path.cwd().resolve()
    if sha(root / CORRECTION_PROTOCOL) != CORRECTION_PROTOCOL_SHA256 or sha(root / ORIGINAL_AUDIT) != ORIGINAL_AUDIT_SHA256:
        raise RuntimeError("B52-D11.1-C1 correction protocol or original audit identity mismatch")
    if sha(result_path) != RESULT_SHA256 or sha(receipt_path) != RECEIPT_SHA256:
        raise RuntimeError("B52-D11.1-C1 immutable formal input identity mismatch")
    frozen_tool = subprocess.run(["git", "show", f"{args.correction_freeze_commit}:{C1_TOOL}"], cwd=root, capture_output=True, check=False)
    frozen_protocol = subprocess.run(["git", "show", f"{CORRECTION_PREREGISTRATION_COMMIT}:{CORRECTION_PROTOCOL}"], cwd=root, capture_output=True, check=False)
    if frozen_tool.returncode != 0 or frozen_tool.stdout != (root / C1_TOOL).read_bytes():
        raise RuntimeError("B52-D11.1-C1 tool does not match its Git freeze commit")
    if frozen_protocol.returncode != 0 or hashlib.sha256(frozen_protocol.stdout).hexdigest() != CORRECTION_PROTOCOL_SHA256:
        raise RuntimeError("B52-D11.1-C1 preregistration Git blob mismatch")
    result_ok, result = valid_hashed_json(result_path, "resultHash")
    receipt_ok, receipt = valid_hashed_json(receipt_path, "receiptHash")
    preflight_ok, preflight = valid_hashed_json(args.preflight, "preflightHash")
    runs = receipt["runs"]
    width, height = spec["scene"]["resolution"]
    source = {(row["fixtureId"], row["frame"], row["sourceRepeat"]): row for row in runs if row["stage"] == "SOURCE"}
    adapters = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ADAPTER"}
    quantizers = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("QUANTIZER_")}
    accumulators = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("ACCUMULATOR_")}
    encoders = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ENCODER"}
    bridges = {(row["fixtureId"], row["sourceRepeat"], row["bridgeRepeat"]): row for row in runs if row["stage"] == "BRIDGE"}
    layer = spec["sourceRender"]["viewLayer"]
    source_checks, scene_checks, source_repeat_checks, adapter_checks, adapter_repeat_checks = [], [], [], [], []
    vector_checks, domain_checks, quantizer_checks, semantic_checks, accumulator_checks = [], [], [], [], []
    invalid_checks, control_checks, static_checks, encoder_checks, bridge_checks = [], [], [], [], []
    replay_rows, decoded_sources = [], {}

    for key, row in source.items():
        parts = multipart(Path(row["exrUri"]))
        decoded_sources[key] = parts
        source_checks.append(row["report"]["output"]["sha256"] == sha(Path(row["exrUri"])) and list(parts) == spec["sourceRender"]["expectedSubimages"])
        fixture = next(item for item in spec["fixtures"] if item["id"] == row["fixtureId"])
        animation = row["report"]["animationStructure"]
        animation_ok = action_exact(animation["camera"], fixture.get("cameraByFrame"))
        animation_ok = animation_ok and all(action_exact(animation["objects"][item["name"]], item.get("locationByFrame")) for item in fixture["objects"])
        scene_checks.append(row["report"]["fixture"] == fixture and row["report"]["runtime"]["seed"] == 521111 and row["report"]["runtime"]["samples"] == 1 and animation_ok)

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for frame in (0, 1):
            first, second = decoded_sources[(fixture_id, frame, 1)], decoded_sources[(fixture_id, frame, 2)]
            source_repeat_checks.append(all(np.array_equal(first[name], second[name]) for name in first))
        repeat_adapters = []
        for repeat in (1, 2):
            previous, current = decoded_sources[(fixture_id, 0, repeat)], decoded_sources[(fixture_id, 1, repeat)]
            expected = {"previousRgba": previous[f"{layer}.Combined"], "currentRgba": current[f"{layer}.Combined"], "previousDepth": previous[f"{layer}.Depth"][..., 0], "currentDepth": current[f"{layer}.Depth"][..., 0], "previousLayer": previous[f"{layer}.Object Index"][..., 0], "currentLayer": current[f"{layer}.Object Index"][..., 0], "motion": np.negative(current[f"{layer}.Vector"][..., :2], dtype=np.float32)}
            adapter_row = adapters[(fixture_id, repeat)]
            actual = adapter_arrays(Path(adapter_row["arraysUri"]), width, height)
            adapter_exact = all(np.array_equal(actual[name], expected[name]) for name in expected)
            adapter_checks.append(adapter_exact)
            repeat_adapters.append(actual)
            mask = owner_mask(spec, fixture)
            vector = current[f"{layer}.Vector"].astype(np.float64)
            xy = np.abs(vector[..., :2][mask] - np.asarray(fixture["expectedVectorXY"])).reshape(-1)
            zw = np.abs(vector[..., 2:][mask] - np.asarray(fixture["expectedVectorZW"])).reshape(-1)
            gate = spec["rawMotionGate"]
            vector_checks.append(bool(np.quantile(xy, 0.99) <= gate["correctEndpointErrorP99MaximumPixels"] and xy.max(initial=0.0) <= gate["correctEndpointErrorAbsoluteMaximumPixels"] and np.quantile(zw, 0.99) <= gate["correctEndpointErrorP99MaximumPixels"] and zw.max(initial=0.0) <= gate["correctEndpointErrorAbsoluteMaximumPixels"]))
            independent = quantize(actual["motion"], spec["quantizerContract"]["acceptanceRadiusPixels"])
            domain_checks.append(independent is not None)
            produced = {}
            for producer in ("python", "node"):
                row = quantizers[(fixture_id, repeat, producer)]
                payload = np.frombuffer(Path(row["outputUri"]).read_bytes(), dtype="<f4").reshape(height, width, 2)
                report_ok, report = valid_hashed_json(Path(row["reportUri"]), "reportHash")
                quantizer_checks.append(report_ok and report["input"]["sha256"] == sha(Path(adapter_row["arraysUri"]) / "motion.xy32") and report["output"]["sha256"] == sha(Path(row["outputUri"])))
                produced[producer] = payload
            quantizer_checks.append(independent is not None and np.array_equal(produced["python"], produced["node"]) and np.array_equal(produced["python"], independent) and np.all(produced["python"][mask] == np.asarray(fixture["expectedD9Motion"], np.float32)))
            arrays = {**actual, "motion": produced["python"]}
            validity, reasons, resolved = replay(arrays)
            _, _, naive = replay(arrays, naive=True)
            _, _, wrong = replay(arrays, sign=-1)
            for probe in fixture["semanticProbes"]:
                x, y = probe["centerTopLeftPixel"]
                expected_reason = ["VALID", "INVALID_BOUNDS", "INVALID_LAYER", "INVALID_DEPTH", "INVALID_ALPHA"].index(probe["expected"])
                semantic_checks.append(bool(np.all(reasons[y - 1 : y + 2, x - 1 : x + 2] == expected_reason)))
            for producer in ("python", "node"):
                directory = Path(accumulators[(fixture_id, repeat, producer)]["arraysUri"])
                accumulator_checks.append((directory / "validity.u8").read_bytes() == validity.tobytes() and (directory / "reason.u8").read_bytes() == reasons.tobytes() and (directory / "resolved.rgba32").read_bytes() == np.ascontiguousarray(resolved, dtype="<f4").tobytes())
            invalid_checks.append(bool(np.array_equal(resolved[validity == 0], actual["currentRgba"][validity == 0])))
            naive_changed, naive_max = difference(naive, resolved)
            wrong_changed, wrong_max = difference(wrong, resolved)
            if fixture_id in spec["sensitivityControls"]["naiveNoLayerOrDepth"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["naiveNoLayerOrDepth"]
                control_checks.append(naive_changed >= threshold["minimumChangedPixels"] and naive_max >= threshold["minimumMaximumAbsoluteDifference"])
            if fixture_id in spec["sensitivityControls"]["wrongMotionSign"]["applicableFixtures"]:
                threshold = spec["sensitivityControls"]["wrongMotionSign"]
                control_checks.append(wrong_changed >= threshold["minimumChangedPixels"] and wrong_max >= threshold["minimumMaximumAbsoluteDifference"])
            if "STATIC" in fixture_id:
                zero = np.ascontiguousarray(produced["python"], dtype="<f4").tobytes() == b"\x00\x00\x00\x00" * produced["python"].size
                static_checks.append(int(validity.sum()) == width * height and np.array_equal(resolved, actual["currentRgba"]) and zero)
            encoded = rgba(Path(encoders[(fixture_id, repeat)]["exrUri"]))
            encoder_checks.append(np.array_equal(encoded, resolved))
            bridge_values = []
            for bridge_repeat in (1, 2):
                value = rgba(Path(bridges[(fixture_id, repeat, bridge_repeat)]["exrUri"]))
                bridge_checks.append(np.array_equal(value, resolved))
                bridge_values.append(value)
            bridge_checks.append(np.array_equal(bridge_values[0], bridge_values[1]))
            replay_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "adapterExact": adapter_exact, "quantizerExact": bool(quantizer_checks[-1]), "validPixels": int(validity.sum()), "resolvedSha256": hashlib.sha256(np.ascontiguousarray(resolved, dtype="<f4").tobytes()).hexdigest()})
        adapter_repeat_checks.append(all(np.array_equal(repeat_adapters[0][name], repeat_adapters[1][name]) for name in ADAPTER_FILES))

    diagnostic_checks = []
    for item in result["diagnostics"]:
        png, sidecar = Path(item["pngUri"]), Path(item["sidecarUri"])
        sidecar_ok, sidecar_payload = valid_hashed_json(sidecar, "sidecarHash")
        diagnostic_checks.append(png.is_file() and sidecar.is_file() and sha(png) == item["pngSha256"] and sha(sidecar) == item["sidecarSha256"] and sidecar_ok and sidecar_payload["png"]["sha256"] == sha(png))
    pids = [row["pid"] for row in runs] + [result["analysisPid"]]
    expected_counts = {"SOURCE": 16, "ADAPTER": 8, "QUANTIZER_PYTHON": 8, "QUANTIZER_NODE": 8, "ACCUMULATOR_PYTHON": 8, "ACCUMULATOR_NODE": 8, "ENCODER": 8, "BRIDGE": 16}
    operation_exact = len(runs) == 80 and all(sum(row["stage"] == stage for row in runs) == count for stage, count in expected_counts.items()) and len(pids) == len(set(pids)) == 81
    evidence = {
        "PARENT_OR_TOOL_IDENTITY": bool(preflight_ok and preflight["parentsMatch"] and preflight["runtimeMatch"] and preflight["allFrozenToolsMatchGit"] and receipt_ok),
        "RUNTIME_OR_DISK_ADMISSION": receipt["diskAdmission"]["status"] == "ACCEPTED",
        "FRESHNESS": bool(preflight["freshnessMatched"] and preflight["formalRootAbsent"]),
        "SCENE_STRUCTURE": len(scene_checks) == 16 and all(scene_checks),
        "SOURCE_RENDER": len(source_checks) == 16 and all(source_checks) and len(source_repeat_checks) == 8 and all(source_repeat_checks),
        "ADAPTER_EXTRACTION": len(adapter_checks) == 8 and all(adapter_checks) and len(adapter_repeat_checks) == 4 and all(adapter_repeat_checks),
        "QUANTIZER_DOMAIN": len(vector_checks) == 8 and all(vector_checks) and len(domain_checks) == 8 and all(domain_checks),
        "QUANTIZER_IDENTITY": len(quantizer_checks) == 24 and all(quantizer_checks) and preflight["contractTests"]["passed"],
        "SEMANTIC_VALIDITY": len(semantic_checks) == 16 and all(semantic_checks),
        "ACCUMULATOR_IDENTITY": len(accumulator_checks) == 16 and all(accumulator_checks) and len(invalid_checks) == 8 and all(invalid_checks),
        "CONTROL_SENSITIVITY": len(control_checks) == 10 and all(control_checks),
        "STATIC_CONTROL": len(static_checks) == 2 and all(static_checks),
        "RAW_EXR_BRIDGE": len(encoder_checks) == 8 and all(encoder_checks) and len(bridge_checks) == 24 and all(bridge_checks),
        "DIAGNOSTIC_OR_OPERATION_IDENTITY": len(diagnostic_checks) == 48 and all(diagnostic_checks) and operation_exact,
    }
    base_failure = next((label for label in spec["baseFailureOrder"] if not evidence[label]), None)
    expected_verdict = spec["decisionRule"]["passVerdict"] if base_failure is None else spec["decisionRule"]["failVerdict"]
    checks = {"specIdentity": sha(args.spec) == SPEC_SHA256, "preflightIdentity": preflight_ok and preflight["status"] == "ACCEPTED", "receiptIdentity": receipt_ok, "resultIdentity": result_ok, "evidenceReplay": result["evidence"] == evidence, "verdictConsistency": result["baseFailure"] == base_failure and result["verdict"] == expected_verdict, "attackTotality": len(result["attacks"]) == len(spec["attacks"]) == 71, "processIdentity": operation_exact, "diagnosticIdentity": len(diagnostic_checks) == 48 and all(diagnostic_checks)}
    status = "PASS" if all(checks.values()) else "FAIL"
    correction = {"protocol": {"uri": CORRECTION_PROTOCOL, "sha256": CORRECTION_PROTOCOL_SHA256, "preregistrationCommit": CORRECTION_PREREGISTRATION_COMMIT}, "originalAudit": {"uri": ORIGINAL_AUDIT, "sha256": ORIGINAL_AUDIT_SHA256}, "c1Tool": {"uri": C1_TOOL, "sha256": sha(root / C1_TOOL), "freezeCommit": args.correction_freeze_commit}, "immutableFormalInputs": {"receiptSha256": RECEIPT_SHA256, "resultSha256": RESULT_SHA256}, "permittedChange": "replay-only NumPy bool_ to native bool plus correction provenance"}
    body = {"schemaVersion": "bfs.blenderNearestIntegerTemporalRecoveryAuditC1.v0.1", "experimentId": spec["experimentId"], "status": status, "auditorPid": os.getpid(), "correction": correction, "spec": {"uri": str(args.spec), "sha256": sha(args.spec)}, "receipt": {"uri": str(receipt_path), "sha256": sha(receipt_path)}, "result": {"uri": str(result_path), "sha256": sha(result_path), "verdict": result["verdict"], "baseFailure": result["baseFailure"]}, "checks": checks, "replayedEvidence": evidence, "replay": replay_rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({**body, "auditHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_1_AUDIT_{status} verdict={result['verdict']} baseFailure={result['baseFailure']} replayCells={len(replay_rows)}")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
