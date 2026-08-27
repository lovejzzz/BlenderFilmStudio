#!/usr/bin/env python3
"""Independent integrity and replay audit for B52-D11."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"
ADAPTER_FILES = {"previousRgba": ("previous.rgba32", 4), "currentRgba": ("current.rgba32", 4), "previousDepth": ("previous-depth.f32", 1), "currentDepth": ("current-depth.f32", 1), "previousLayer": ("previous-layer.f32", 1), "currentLayer": ("current-layer.f32", 1), "motion": ("motion.xy32", 2)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def valid_hashed_json(path: Path, field: str) -> tuple[bool, dict]:
    payload = json.loads(path.read_text())
    body = {key: value for key, value in payload.items() if key != field}
    return payload.get(field) == canonical_hash(body), payload


def multipart(path: Path) -> dict[str, np.ndarray]:
    first = oiio.ImageBuf(str(path), 0, 0)
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
    spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), np.float32).reshape(spec.height, spec.width, 4)
    image.close()
    return np.ascontiguousarray(pixels, dtype="<f4")


def adapter_arrays(directory: Path, width: int, height: int) -> dict[str, np.ndarray]:
    result = {}
    for name, (filename, components) in ADAPTER_FILES.items():
        shape = (height, width, components) if components > 1 else (height, width)
        result[name] = np.frombuffer((directory / filename).read_bytes(), dtype="<f4").reshape(shape)
    return result


def replay(arrays: dict[str, np.ndarray]) -> tuple[bytes, bytes, bytes]:
    height, width = arrays["currentDepth"].shape
    validity = bytearray(width * height)
    reasons = bytearray(width * height)
    resolved = arrays["currentRgba"].copy()
    for y in range(height):
        for x in range(width):
            index = y * width + x
            dx, dy = int(float(arrays["motion"][y, x, 0])), int(float(arrays["motion"][y, x, 1]))
            qx, qy = x - dx, y + dy
            if not (0 <= qx < width and 0 <= qy < height):
                reason = 1
            elif arrays["previousLayer"][qy, qx] != arrays["currentLayer"][y, x]:
                reason = 2
            elif abs(float(arrays["previousDepth"][qy, qx]) - float(arrays["currentDepth"][y, x])) > max(1.0, float(arrays["currentDepth"][y, x])) / 1024.0:
                reason = 3
            elif arrays["previousRgba"][qy, qx, 3] <= 0 or arrays["currentRgba"][y, x, 3] <= 0:
                reason = 4
            else:
                reason = 0
            reasons[index] = reason
            if reason == 0:
                validity[index] = 1
                for channel in range(4):
                    resolved[y, x, channel] = np.float32(0.5 * float(arrays["currentRgba"][y, x, channel]) + 0.5 * float(arrays["previousRgba"][qy, qx, channel]))
    return bytes(validity), bytes(reasons), np.ascontiguousarray(resolved, dtype="<f4").tobytes()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    if sha(args.spec) != SPEC_SHA256 or args.output.exists():
        raise RuntimeError("B52-D11 audit identity/output mismatch")
    result_path, receipt_path = args.formal_root / "results.json", args.formal_root / "run.receipt.json"
    result_ok, result = valid_hashed_json(result_path, "resultHash")
    receipt_ok, receipt = valid_hashed_json(receipt_path, "receiptHash")
    preflight_ok, preflight = valid_hashed_json(args.preflight, "preflightHash")
    runs = receipt["runs"]
    width, height = spec["scene"]["resolution"]
    source = {(row["fixtureId"], row["frame"], row["sourceRepeat"]): row for row in runs if row["stage"] == "SOURCE"}
    adapters = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ADAPTER"}
    accumulators = {(row["fixtureId"], row["sourceRepeat"], row["producer"]): row for row in runs if row["stage"].startswith("ACCUMULATOR_")}
    encoders = {(row["fixtureId"], row["sourceRepeat"]): row for row in runs if row["stage"] == "ENCODER"}
    bridges = {(row["fixtureId"], row["sourceRepeat"], row["bridgeRepeat"]): row for row in runs if row["stage"] == "BRIDGE"}
    layer = spec["sourceRender"]["viewLayer"]
    source_rows, adapter_rows, accumulator_rows, encoder_rows, bridge_rows = [], [], [], [], []
    integer_mismatches = 0
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        for repeat in (1, 2):
            previous_row, current_row = source[(fixture_id, 0, repeat)], source[(fixture_id, 1, repeat)]
            previous, current = multipart(Path(previous_row["exrUri"])), multipart(Path(current_row["exrUri"]))
            source_exact = all(row["report"]["output"]["sha256"] == sha(Path(row["exrUri"])) for row in (previous_row, current_row))
            source_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "match": source_exact})
            expected = {"previousRgba": previous[f"{layer}.Combined"], "currentRgba": current[f"{layer}.Combined"], "previousDepth": previous[f"{layer}.Depth"][..., 0], "currentDepth": current[f"{layer}.Depth"][..., 0], "previousLayer": previous[f"{layer}.Object Index"][..., 0], "currentLayer": current[f"{layer}.Object Index"][..., 0], "motion": np.negative(current[f"{layer}.Vector"][..., :2], dtype=np.float32)}
            adapter_row = adapters[(fixture_id, repeat)]
            actual = adapter_arrays(Path(adapter_row["arraysUri"]), width, height)
            adapter_exact = all(np.array_equal(actual[name], expected[name]) for name in expected)
            adapter_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "match": adapter_exact})
            validity, reasons, resolved = replay(actual)
            for producer in ("python", "node"):
                directory = Path(accumulators[(fixture_id, repeat, producer)]["arraysUri"])
                match = (directory / "validity.u8").read_bytes() == validity and (directory / "reason.u8").read_bytes() == reasons and (directory / "resolved.rgba32").read_bytes() == resolved
                accumulator_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "producer": producer, "match": match})
            encoded = rgba(Path(encoders[(fixture_id, repeat)]["exrUri"]))
            encoded_exact = encoded.tobytes() == resolved
            encoder_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "match": encoded_exact})
            decoded = []
            for bridge_repeat in (1, 2):
                value = rgba(Path(bridges[(fixture_id, repeat, bridge_repeat)]["exrUri"]))
                match = value.tobytes() == resolved
                decoded.append(value)
                bridge_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "bridgeRepeat": bridge_repeat, "match": match})
            bridge_rows.append({"fixtureId": fixture_id, "sourceRepeat": repeat, "repeatIdentity": bool(np.array_equal(decoded[0], decoded[1])), "match": bool(np.array_equal(decoded[0], decoded[1]))})
            if fixture_id != "REAL_TEXTURED_STATIC_CONTROL_197X113":
                expected_motion = np.asarray(fixture["expectedD9Motion"], np.int64)
                integer_mismatches += int(np.count_nonzero(np.any(np.trunc(actual["motion"]).astype(np.int64) != expected_motion, axis=2)))
    diagnostic_rows = []
    for item in result["diagnostics"]:
        png, sidecar = Path(item["pngUri"]), Path(item["sidecarUri"])
        sidecar_ok, sidecar_payload = valid_hashed_json(sidecar, "sidecarHash")
        match = png.is_file() and sidecar.is_file() and sha(png) == item["pngSha256"] and sha(sidecar) == item["sidecarSha256"] and sidecar_ok and sidecar_payload["png"]["sha256"] == sha(png)
        diagnostic_rows.append({"fixtureId": item["fixtureId"], "name": item["name"], "match": match})
    pids = [row["pid"] for row in runs] + [result["analysisPid"]]
    process_exact = len(runs) == 64 and len(pids) == len(set(pids)) == 65 and result["operationCounts"]["totalChildProcesses"] == 65
    expected_failure = "MOTION_INTEGERIZATION" if integer_mismatches else None
    verdict_consistent = result["baseFailure"] == expected_failure and result["verdict"] == (spec["decisionRule"]["failVerdict"] if expected_failure else spec["decisionRule"]["passVerdict"])
    checks = {
        "specIdentity": sha(args.spec) == SPEC_SHA256,
        "preflightIdentity": preflight_ok and preflight["status"] == "ACCEPTED" and preflight["allFrozenToolsMatchGit"],
        "receiptIdentity": receipt_ok,
        "resultIdentity": result_ok,
        "sourceReplay": len(source_rows) == 8 and all(row["match"] for row in source_rows),
        "adapterReplay": len(adapter_rows) == 8 and all(row["match"] for row in adapter_rows),
        "accumulatorReplay": len(accumulator_rows) == 16 and all(row["match"] for row in accumulator_rows),
        "encoderReplay": len(encoder_rows) == 8 and all(row["match"] for row in encoder_rows),
        "bridgeReplay": len(bridge_rows) == 24 and all(row["match"] for row in bridge_rows),
        "diagnosticIdentity": len(diagnostic_rows) == 40 and all(row["match"] for row in diagnostic_rows),
        "processIdentity": process_exact,
        "verdictConsistency": verdict_consistent,
        "attackTotality": len(result["attacks"]) == len(spec["attacks"]) == 56,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    body = {"schemaVersion": "bfs.blenderRealTexturedTemporalAudit.v0.1", "experimentId": spec["experimentId"], "status": status, "auditorPid": os.getpid(), "spec": {"uri": str(args.spec), "sha256": sha(args.spec)}, "receipt": {"uri": str(receipt_path), "sha256": sha(receipt_path)}, "result": {"uri": str(result_path), "sha256": sha(result_path), "verdict": result["verdict"], "baseFailure": result["baseFailure"]}, "checks": checks, "integerizationMismatchPixelsAcrossMovingFrames": integer_mismatches, "replay": {"sources": source_rows, "adapters": adapter_rows, "accumulators": accumulator_rows, "encoders": encoder_rows, "bridges": bridge_rows, "diagnostics": diagnostic_rows}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({**body, "auditHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_AUDIT_{status} verdict={result['verdict']} baseFailure={result['baseFailure']} mismatches={integer_mismatches}")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
