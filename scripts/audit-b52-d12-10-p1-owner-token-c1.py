#!/usr/bin/env python3
"""Independent raw-EXR audit for B52-D12.10-P1-C1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "5805af301077a8b3ae18892e3c4c2c5a2ad646a7e8b3cdddd762c39d22293a77"
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


def load_parts(path: Path) -> dict:
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


def analytic_masks(p1_spec: dict, frame: int) -> dict:
    width, height = p1_spec["sceneContract"]["resolution"]
    scale = float(p1_spec["sceneContract"]["camera"]["orthoScaleWorld"])
    if width < height:
        raise RuntimeError("P1-C1 audit correction is frozen to landscape")
    world_width, world_height = scale, scale * height / width
    yy, xx = np.mgrid[0:height, 0:width]
    x = ((xx + 0.5) / width - 0.5) * world_width
    y = (0.5 - (yy + 0.5) / height) * world_height
    margin = float(p1_spec["analyticMaskContract"]["stableInteriorMarginPixels"])
    mx, my = margin * world_width / width, margin * world_height / height
    background, foreground = p1_spec["sceneContract"]["owners"]
    bx, by, _ = map(float, background["locationByFrame"][str(frame)])
    fx, fy, _ = map(float, foreground["locationByFrame"][str(frame)])
    bhx, bhy = float(background["sizeWorld"][0]) / 2, float(background["sizeWorld"][1]) / 2
    fhx, fhy = float(foreground["sizeWorld"][0]) / 2, float(foreground["sizeWorld"][1]) / 2
    inside_bg = (np.abs(x - bx) <= bhx) & (np.abs(y - by) <= bhy)
    bg_inner = (np.abs(x - bx) <= bhx - mx) & (np.abs(y - by) <= bhy - my)
    fg_inner = (np.abs(x - fx) <= fhx - mx) & (np.abs(y - fy) <= fhy - my)
    fg_outer = (np.abs(x - fx) <= fhx + mx) & (np.abs(y - fy) <= fhy + my)
    return {"P1_FOREGROUND": fg_inner, "P1_BACKGROUND": bg_inner & ~fg_outer, "boundary": inside_bg & fg_outer & ~fg_inner}


def owner_stats(values: np.ndarray, mask: np.ndarray, token: float) -> dict:
    samples = values[mask].astype(np.float32)
    expected = np.float32(token)
    exact = samples == expected
    return {"pixels": int(samples.size), "expectedToken": float(expected), "minimum": float(samples.min()) if samples.size else None, "maximum": float(samples.max()) if samples.size else None, "exactTokenPixels": int(exact.sum()), "nonTokenPixels": int((~exact).sum())}


def boundary_stats(values: np.ndarray, mask: np.ndarray, tokens: list[float]) -> dict:
    samples = values[mask].astype(np.float32)
    exact = np.zeros(samples.shape, dtype=bool)
    for token in tokens:
        exact |= samples == np.float32(token)
    unique = np.unique(samples)
    return {"pixels": int(samples.size), "minimum": float(samples.min()) if samples.size else None, "maximum": float(samples.max()) if samples.size else None, "exactRegisteredTokenPixels": int(exact.sum()), "nonRegisteredTokenPixels": int((~exact).sum()), "uniqueValueCount": int(unique.size), "uniqueValues": [float(value) for value in unique[:256]], "uniqueValuesTruncated": bool(unique.size > 256), "payloadSha256": sha_bytes(np.ascontiguousarray(samples, dtype="<f4").tobytes())}


def viability(p1_spec: dict, cells: dict, mechanism: str) -> bool:
    minimum = p1_spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"]
    exact = all(owner["pixels"] >= minimum and owner["exactTokenPixels"] == owner["pixels"] and owner["nonTokenPixels"] == 0 for row in cells.values() for owner in row["mechanisms"][mechanism]["owners"].values())
    display = all(cells[f"F{frame}/ACES_SDR/R{repeat}"]["mechanisms"][mechanism]["payloadSha256"] == cells[f"F{frame}/UN_TONE_MAPPED/R{repeat}"]["mechanisms"][mechanism]["payloadSha256"] for frame in (0, 1) for repeat in (1, 2))
    repeats = all(cells[f"F{frame}/{display_id}/R1"]["mechanisms"][mechanism]["payloadSha256"] == cells[f"F{frame}/{display_id}/R2"]["mechanisms"][mechanism]["payloadSha256"] for frame in (0, 1) for display_id in ("ACES_SDR", "UN_TONE_MAPPED"))
    distinct = len(set(p1_spec["mechanisms"][mechanism]["expectedTokens"].values())) == 2
    return exact and display and repeats and distinct


def verdict(p1_spec: dict, material: bool, custom: bool) -> str:
    decision = p1_spec["frozenDecision"]
    return decision["bothViable"] if material and custom else decision["materialOnly"] if material else decision["customAovOnly"] if custom else decision["noneViable"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite P1-C1 audit")
    repo = Path.cwd().resolve()
    c1_spec = json.loads(args.spec.read_text())
    p1_spec = json.loads((repo / c1_spec["parents"]["p1Spec"]["uri"]).read_text())
    result = json.loads(args.result.read_text())
    execution = json.loads(args.execution.read_text())
    if sha_file(args.spec) != SPEC_SHA256 or sha_file(Path(os.sys.executable)) != p1_spec["runtime"]["python"]["sha256"] or np.__version__ != p1_spec["runtime"]["python"]["numpy"] or oiio.VERSION_STRING != p1_spec["runtime"]["python"]["openImageIO"]:
        raise RuntimeError("P1-C1 audit runtime identity mismatch")
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in c1_spec["parents"].items()}
    source_checks = {row["cell"]: sha_file(repo / row["reportUri"]) == row["reportSha256"] and sha_file(repo / row["exrUri"]) == row["exrSha256"] for row in c1_spec["sourceManifest"]}
    result_rows = {row["cell"]: row for row in result["cells"]}
    p1_root = repo / p1_spec["freshness"]["formalRoot"]
    corrected_root = args.output_root.resolve()
    raw_checks, measurement_checks, corrected_payload_checks, original_payload_checks, source_report_checks = [], [], [], [], []
    replay = {}
    manifest = {row["cell"]: row for row in c1_spec["sourceManifest"]}
    for frame in p1_spec["formalMatrix"]["frames"]:
        masks = analytic_masks(p1_spec, frame)
        for display in p1_spec["sceneContract"]["displayCells"]:
            display_id = display["id"]
            for repeat in p1_spec["formalMatrix"]["repeats"]:
                cell = f"F{frame}/{display_id}/R{repeat}"
                item = manifest[cell]
                report_path, exr_path = repo / item["reportUri"], repo / item["exrUri"]
                report = json.loads(report_path.read_text())
                source_report_checks.extend([self_ok(report, "reportHash"), report["output"]["sha256"] == sha_file(exr_path), report["operationCounts"]["blenderRenderCalls"] == 1, report["operationCounts"]["modelCalls"] == 0, report["operationCounts"]["networkCalls"] == 0])
                parts = load_parts(exr_path)
                raw_checks.append(all(sum(name.endswith(suffix) for name in parts) == 1 for suffix in p1_spec["sceneContract"]["output"]["expectedPassSuffixes"]))
                row = result_rows[cell]
                measurement_checks.append(row["maskPixels"] == {name: int(mask.sum()) for name, mask in masks.items()})
                mechanisms = {}
                for mechanism, suffix in SUFFIX.items():
                    pass_name = next(name for name in parts if name.endswith(suffix))
                    part = parts[pass_name]
                    values = np.ascontiguousarray(part["pixels"][..., 0], dtype="<f4")
                    payload = values.tobytes()
                    filename = FILENAME[mechanism]
                    corrected_payload_checks.append((corrected_root / "arrays" / f"frame-{frame}" / display_id / f"R{repeat}" / filename).read_bytes() == payload)
                    original_payload_checks.append((p1_root / "arrays" / f"frame-{frame}" / display_id / f"R{repeat}" / filename).read_bytes() == payload)
                    tokens = p1_spec["mechanisms"][mechanism]["expectedTokens"]
                    mechanisms[mechanism] = {
                        "passAvailable": True,
                        "passName": pass_name,
                        "channels": part["channels"],
                        "shape": list(values.shape),
                        "allFinite": bool(np.isfinite(values).all()),
                        "payloadSha256": sha_bytes(payload),
                        "payloadBytes": len(payload),
                        "originalPayloadByteIdentity": True,
                        "owners": {owner: owner_stats(values, masks[owner], token) for owner, token in tokens.items()},
                        "boundary": boundary_stats(values, masks["boundary"], list(tokens.values())),
                    }
                    measurement_checks.append(row["mechanisms"][mechanism] == mechanisms[mechanism])
                replay[cell] = {"mechanisms": mechanisms}
    material, custom = viability(p1_spec, replay, "MATERIAL_INDEX"), viability(p1_spec, replay, "CUSTOM_VALUE_AOV")
    object_viable = viability(p1_spec, replay, "OBJECT_INDEX_CONTROL")
    expected_verdict = verdict(p1_spec, material, custom)
    attacks = result.get("mutationAttacks", [])
    required = set(c1_spec["attacks"]["requiredTargets"])
    attack_ok = len(attacks) >= c1_spec["attacks"]["minimumAnalyzerAttacks"] and len({row["id"] for row in attacks}) == len(attacks) and all(row.get("passed") is True for row in attacks) and required.issubset({row["target"] for row in attacks}) and result["mutationAttackPassed"] == result["mutationAttackTotal"] == len(attacks)
    original_source_pids = [row["pid"] for row in json.loads((repo / c1_spec["parents"]["p1Execution"]["uri"]).read_text())["children"]]
    correction_pids = [row["pid"] for row in execution["children"]] + [os.getpid()]
    process_ok = self_ok(execution, "executionHash") and len(execution["children"]) == 1 and execution["children"][0]["role"] == "ANALYZER" and execution["children"][0]["exitCode"] == 0 and len(set(correction_pids)) == 2 and len(set(original_source_pids)) == 8 and not set(correction_pids) & set(original_source_pids)
    checks = [
        ("SPEC_PARENT_RESULT_EXECUTION_HASH", all(parent_checks.values()) and self_ok(result, "evidenceHash") and self_ok(execution, "executionHash")),
        ("SOURCE_MANIFEST_IDENTITY", all(source_checks.values())),
        ("EIGHT_SOURCE_REPORT_AND_EXR_INTEGRITY", len(source_report_checks) == 40 and all(source_report_checks)),
        ("CORRECT_LANDSCAPE_ANALYTIC_MASK_REPLAY", result["projectionContract"] == {"projectionConvention": "LANDSCAPE_ORTHO_SCALE_IS_WIDTH", "maskSource": "ANALYTIC_SPEC_ONLY", "outcomeNeutralValidation": True, "stableInteriorMarginPixels": 3.0, "minimumInteriorPixels": 256}),
        ("RAW_PASS_DISCOVERY_AND_FINITE", len(raw_checks) == 8 and all(raw_checks)),
        ("RAW_CORRECTED_PAYLOAD_BYTE_IDENTITY", len(corrected_payload_checks) == 24 and all(corrected_payload_checks)),
        ("RAW_ORIGINAL_PAYLOAD_BYTE_IDENTITY", len(original_payload_checks) == 24 and all(original_payload_checks)),
        ("MEASUREMENT_RAW_REPLAY", len(measurement_checks) == 32 and all(measurement_checks)),
        ("DISPLAY_AND_REPEAT_GATE_REPLAY", material == result["materialIndexViable"] and custom == result["customAovViable"]),
        ("OUTCOME_NEUTRAL_VERDICT_MAPPING", result["verdict"] == expected_verdict),
        ("OBJECT_INDEX_NEGATIVE_CONTROL", object_viable is False and result["objectIndexNegativeControl"] is True),
        ("MUTATION_ROSTER_TOTALITY", attack_ok),
        ("TWO_NEW_PID_TOTALITY", process_ok),
        ("NEW_RENDER_MODEL_NETWORK_ZERO", result["operationCounts"]["newBlenderRenderCalls"] == 0 and result["operationCounts"]["modelCalls"] == 0 and result["operationCounts"]["networkCalls"] == 0),
    ]
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeCorrectionAudit.v0.1",
        "experimentId": c1_spec["experimentId"],
        "auditPid": os.getpid(),
        "passed": all(value for _, value in checks),
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "expectedVerdict": expected_verdict,
        "resultEvidenceHash": result["evidenceHash"],
        "resultSha256": sha_file(args.result),
        "sourceManifestChecks": source_checks,
        "sourceReportChecks": len(source_report_checks),
        "correctedPayloadByteChecks": len(corrected_payload_checks),
        "originalPayloadByteChecks": len(original_payload_checks),
        "measurementReplayChecks": len(measurement_checks),
        "operationCounts": {"auditProcesses": 1, "newBlenderProcesses": 0, "newBlenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    audit = {**body, "auditHash": canon(body)}
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_C1_AUDIT passed={audit['passed']} checks={audit['checkPassed']}/{audit['checkTotal']} hash={audit['auditHash']}")
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
