#!/usr/bin/env python3
"""Independent raw-EXR audit for B52-D12.10-P1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be"
SUFFIX = {"OBJECT_INDEX_CONTROL": ".Object Index", "MATERIAL_INDEX": ".Material Index", "CUSTOM_VALUE_AOV": ".OwnerToken"}
FILENAME = {"OBJECT_INDEX_CONTROL": "object-index.f32", "MATERIAL_INDEX": "material-index.f32", "CUSTOM_VALUE_AOV": "owner-token-aov.f32"}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canon({key: item for key, item in value.items() if key != field})


def load(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    output = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        if pixels.ndim == 2:
            pixels = pixels[..., np.newaxis]
        output[name] = {"pixels": pixels, "channels": list(image_spec.channelnames)}
    return output


def mask_set(spec: dict, frame: int) -> dict:
    width, height = spec["sceneContract"]["resolution"]
    world_height = float(spec["sceneContract"]["camera"]["orthoScaleWorld"])
    world_width = world_height * width / height
    yy, xx = np.mgrid[0:height, 0:width]
    world_x = ((xx + 0.5) / width - 0.5) * world_width
    world_y = (0.5 - (yy + 0.5) / height) * world_height
    margin = float(spec["analyticMaskContract"]["stableInteriorMarginPixels"])
    mx, my = margin * world_width / width, margin * world_height / height
    background, foreground = spec["sceneContract"]["owners"]
    bx, by, _ = map(float, background["locationByFrame"][str(frame)])
    fx, fy, _ = map(float, foreground["locationByFrame"][str(frame)])
    bhx, bhy = float(background["sizeWorld"][0]) / 2, float(background["sizeWorld"][1]) / 2
    fhx, fhy = float(foreground["sizeWorld"][0]) / 2, float(foreground["sizeWorld"][1]) / 2
    bg = (np.abs(world_x - bx) <= bhx) & (np.abs(world_y - by) <= bhy)
    bg_inner = (np.abs(world_x - bx) <= bhx - mx) & (np.abs(world_y - by) <= bhy - my)
    fg_inner = (np.abs(world_x - fx) <= fhx - mx) & (np.abs(world_y - fy) <= fhy - my)
    fg_outer = (np.abs(world_x - fx) <= fhx + mx) & (np.abs(world_y - fy) <= fhy + my)
    return {"P1_FOREGROUND": fg_inner, "P1_BACKGROUND": bg_inner & ~fg_outer, "boundary": bg & fg_outer & ~fg_inner}


def owner_measure(values: np.ndarray, mask: np.ndarray, token: float) -> dict:
    samples = values[mask].astype(np.float32)
    expected = np.float32(token)
    exact = samples == expected
    return {"pixels": int(samples.size), "expectedToken": float(expected), "minimum": float(samples.min()) if samples.size else None, "maximum": float(samples.max()) if samples.size else None, "exactTokenPixels": int(exact.sum()), "nonTokenPixels": int((~exact).sum())}


def boundary_measure(values: np.ndarray, mask: np.ndarray, tokens: list[float]) -> dict:
    samples = values[mask].astype(np.float32)
    exact = np.zeros(samples.shape, dtype=bool)
    for token in tokens:
        exact |= samples == np.float32(token)
    unique = np.unique(samples)
    return {"pixels": int(samples.size), "minimum": float(samples.min()) if samples.size else None, "maximum": float(samples.max()) if samples.size else None, "exactRegisteredTokenPixels": int(exact.sum()), "nonRegisteredTokenPixels": int((~exact).sum()), "uniqueValueCount": int(unique.size), "uniqueValues": [float(value) for value in unique[:256]], "uniqueValuesTruncated": bool(unique.size > 256), "payloadSha256": sha_bytes(np.ascontiguousarray(samples, dtype="<f4").tobytes())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12.10-P1 audit")
    spec = json.loads(args.spec.read_text())
    execution = json.loads(args.execution.read_text())
    result = json.loads(args.result.read_text())
    if sha_file(args.spec) != SPEC_SHA256 or sha_file(Path(os.sys.executable)) != spec["runtime"]["python"]["sha256"] or np.__version__ != spec["runtime"]["python"]["numpy"] or oiio.VERSION_STRING != spec["runtime"]["python"]["openImageIO"]:
        raise RuntimeError("D12.10-P1 audit identity mismatch")
    result_rows = {row["cell"]: row for row in result["cells"]}
    raw_checks, measurement_checks, payload_checks, source_checks = [], [], [], []
    hashes = {mechanism: {} for mechanism in SUFFIX}
    for frame in spec["formalMatrix"]["frames"]:
        masks = mask_set(spec, frame)
        for display in spec["sceneContract"]["displayCells"]:
            display_id = display["id"]
            for repeat in spec["formalMatrix"]["repeats"]:
                cell = f"F{frame}/{display_id}/R{repeat}"
                row = result_rows[cell]
                source = args.root / "sources" / f"frame-{frame}" / display_id / f"R{repeat}"
                report_path, exr_path = source / "report.json", source / "source.exr"
                report = json.loads(report_path.read_text())
                source_checks.extend([
                    self_ok(report, "reportHash"),
                    report["output"]["sha256"] == sha_file(exr_path),
                    report["operationCounts"] == {"blenderProcesses": 1, "blenderRenderCalls": 1, "cyclesRayRenders": 1, "modelCalls": 0, "networkCalls": 0},
                    report["runtime"]["executableSha256"] == spec["runtime"]["blender"]["sha256"],
                    report["frame"] == frame and report["displayCell"] == display_id and report["repeat"] == repeat,
                ])
                loaded = load(exr_path)
                raw_checks.append(all(sum(name.endswith(suffix) for name in loaded) == 1 for suffix in spec["sceneContract"]["output"]["expectedPassSuffixes"]))
                measurement_checks.append(row["maskPixels"] == {name: int(mask.sum()) for name, mask in masks.items()})
                for mechanism, suffix in SUFFIX.items():
                    pass_name = next(name for name in loaded if name.endswith(suffix))
                    part = loaded[pass_name]
                    raw_checks.append(part["pixels"].shape[-1] == 1 and np.isfinite(part["pixels"]).all())
                    values = np.ascontiguousarray(part["pixels"][..., 0], dtype="<f4")
                    payload = values.tobytes()
                    payload_sha = sha_bytes(payload)
                    hashes[mechanism][(frame, display_id, repeat)] = payload_sha
                    array_path = args.root / "arrays" / f"frame-{frame}" / display_id / f"R{repeat}" / FILENAME[mechanism]
                    payload_checks.append(array_path.read_bytes() == payload)
                    tokens = spec["mechanisms"][mechanism]["expectedTokens"]
                    recomputed = {
                        "passAvailable": True,
                        "passName": pass_name,
                        "channels": part["channels"],
                        "shape": list(values.shape),
                        "allFinite": bool(np.isfinite(values).all()),
                        "payloadSha256": payload_sha,
                        "payloadBytes": len(payload),
                        "owners": {owner: owner_measure(values, masks[owner], token) for owner, token in tokens.items()},
                        "boundary": boundary_measure(values, masks["boundary"], list(tokens.values())),
                    }
                    measurement_checks.append(row["mechanisms"][mechanism] == recomputed)
    invariance_checks = []
    mechanism_viability = {}
    for mechanism, values in hashes.items():
        display_ok = all(values[(frame, "ACES_SDR", repeat)] == values[(frame, "UN_TONE_MAPPED", repeat)] for frame in (0, 1) for repeat in (1, 2))
        repeat_ok = all(values[(frame, display, 1)] == values[(frame, display, 2)] for frame in (0, 1) for display in ("ACES_SDR", "UN_TONE_MAPPED"))
        exact = all(owner["nonTokenPixels"] == 0 and owner["exactTokenPixels"] == owner["pixels"] and owner["pixels"] >= spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"] for row in result_rows.values() for owner in row["mechanisms"][mechanism]["owners"].values())
        distinguishes = len(set(spec["mechanisms"][mechanism]["expectedTokens"].values())) == 2
        invariance_checks.extend([display_ok, repeat_ok])
        mechanism_viability[mechanism] = exact and display_ok and repeat_ok and distinguishes
    material, custom = mechanism_viability["MATERIAL_INDEX"], mechanism_viability["CUSTOM_VALUE_AOV"]
    decision = spec["frozenDecision"]
    expected_verdict = decision["bothViable"] if material and custom else decision["materialOnly"] if material else decision["customAovOnly"] if custom else decision["noneViable"]
    attacks = result.get("mutationAttacks", [])
    required_targets = set(spec["attacks"]["requiredTargets"])
    attack_ok = len(attacks) >= spec["attacks"]["minimumRegisteredAttacks"] and len({row["id"] for row in attacks}) == len(attacks) and all(row.get("passed") is True for row in attacks) and required_targets.issubset({row["target"] for row in attacks}) and result.get("mutationAttackPassed") == result.get("mutationAttackTotal") == len(attacks)
    source_pids = [row["pid"] for row in execution["children"]]
    pids = source_pids + [result["analyzerPid"], os.getpid()]
    process_ok = self_ok(execution, "executionHash") and len(source_pids) == 8 and len(pids) == len(set(pids)) == spec["formalMatrix"]["expectedUniqueChildProcesses"] and all(row["exitCode"] == 0 for row in execution["children"])
    checks = [
        ("SPEC_RESULT_EXECUTION_HASH", self_ok(result, "evidenceHash") and self_ok(execution, "executionHash")),
        ("TEN_PID_TOTALITY", process_ok),
        ("SOURCE_REPORT_AND_EXR_IDENTITY", all(source_checks)),
        ("RAW_PASS_DISCOVERY_AND_FINITE", all(raw_checks)),
        ("EXTRACTED_PAYLOAD_BYTE_IDENTITY", len(payload_checks) == 24 and all(payload_checks)),
        ("MEASUREMENT_RAW_REPLAY", len(measurement_checks) == 32 and all(measurement_checks)),
        ("DISPLAY_AND_REPEAT_INVARIANCE", all(invariance_checks)),
        ("VERDICT_MAPPING", result["verdict"] == expected_verdict and result["materialIndexViable"] == material and result["customAovViable"] == custom),
        ("OBJECT_INDEX_NEGATIVE_CONTROL", mechanism_viability["OBJECT_INDEX_CONTROL"] is False and result["objectIndexNegativeControl"] is True),
        ("MUTATION_ROSTER_TOTALITY", attack_ok),
        ("MODEL_NETWORK_ZERO", result["operationCounts"]["modelCalls"] == 0 and result["operationCounts"]["networkCalls"] == 0),
    ]
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeAudit.v0.1",
        "experimentId": spec["experimentId"],
        "auditPid": os.getpid(),
        "passed": all(value for _, value in checks),
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "expectedVerdict": expected_verdict,
        "resultEvidenceHash": result["evidenceHash"],
        "resultSha256": sha_file(args.result),
        "rawSourceCount": len(result_rows),
        "rawPassChecks": len(raw_checks),
        "payloadByteChecks": len(payload_checks),
        "measurementReplayChecks": len(measurement_checks),
        "operationCounts": {"auditProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canon(body)}
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_AUDIT passed={audit['passed']} checks={audit['checkPassed']}/{audit['checkTotal']} hash={audit['auditHash']}")
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
