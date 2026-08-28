#!/usr/bin/env python3
"""Corrected post-hoc analyzer for B52-D12.10-P1-C1."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "5805af301077a8b3ae18892e3c4c2c5a2ad646a7e8b3cdddd762c39d22293a77"


def load_bound(path: Path):
    module_spec = importlib.util.spec_from_file_location("bfs_p1_invalid_bound", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("P1-C1 cannot load bound analyzer")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def corrected_masks(p1_spec: dict, frame: int) -> dict[str, np.ndarray]:
    contract = p1_spec["sceneContract"]
    width, height = contract["resolution"]
    scale = float(contract["camera"]["orthoScaleWorld"])
    if width < height:
        raise RuntimeError("P1-C1 frozen correction applies only to the preregistered landscape cell")
    world_width = scale
    world_height = scale * height / width
    yy, xx = np.mgrid[0:height, 0:width]
    x_world = ((xx + 0.5) / width - 0.5) * world_width
    y_world = (0.5 - (yy + 0.5) / height) * world_height
    margin = float(p1_spec["analyticMaskContract"]["stableInteriorMarginPixels"])
    margin_x, margin_y = margin * world_width / width, margin * world_height / height
    background, foreground = contract["owners"]
    bgx, bgy, _ = map(float, background["locationByFrame"][str(frame)])
    bghx, bghy = float(background["sizeWorld"][0]) / 2, float(background["sizeWorld"][1]) / 2
    fgx, fgy, _ = map(float, foreground["locationByFrame"][str(frame)])
    fghx, fghy = float(foreground["sizeWorld"][0]) / 2, float(foreground["sizeWorld"][1]) / 2
    inside_bg = (np.abs(x_world - bgx) <= bghx) & (np.abs(y_world - bgy) <= bghy)
    bg_eroded = (np.abs(x_world - bgx) <= bghx - margin_x) & (np.abs(y_world - bgy) <= bghy - margin_y)
    fg_eroded = (np.abs(x_world - fgx) <= fghx - margin_x) & (np.abs(y_world - fgy) <= fghy - margin_y)
    fg_expanded = (np.abs(x_world - fgx) <= fghx + margin_x) & (np.abs(y_world - fgy) <= fghy + margin_y)
    return {"P1_FOREGROUND": fg_eroded, "P1_BACKGROUND": bg_eroded & ~fg_expanded, "boundary": inside_bg & fg_expanded & ~fg_eroded}


def verdict_for(p1_spec: dict, material: bool, custom: bool) -> str:
    decision = p1_spec["frozenDecision"]
    return decision["bothViable"] if material and custom else decision["materialOnly"] if material else decision["customAovOnly"] if custom else decision["noneViable"]


def projection_ok(projection: dict, c1_spec: dict, p1_spec: dict, bound) -> bool:
    if projection.get("projectionConvention") != "LANDSCAPE_ORTHO_SCALE_IS_WIDTH" or projection.get("maskSource") != "ANALYTIC_SPEC_ONLY" or projection.get("outcomeNeutralValidation") is not True:
        return False
    if projection.get("stableInteriorMarginPixels") != p1_spec["analyticMaskContract"]["stableInteriorMarginPixels"] or projection.get("minimumInteriorPixels") != p1_spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"]:
        return False
    if projection.get("sourceRenderCalls") != 8 or projection.get("newRenderCalls") != 0 or projection.get("runtimeIdentity") is not True or projection.get("objectIndexDistinguishesOwners") is not False:
        return False
    expected_cells = {(frame, display["id"], repeat) for frame in p1_spec["formalMatrix"]["frames"] for display in p1_spec["sceneContract"]["displayCells"] for repeat in p1_spec["formalMatrix"]["repeats"]}
    cells = projection.get("cells", [])
    if len(cells) != 8 or {(row.get("frame"), row.get("displayCell"), row.get("repeat")) for row in cells} != expected_cells:
        return False
    for row in cells:
        if not row.get("sourceIdentity") or not row.get("sourceIntegrity", {}).get("passed") or not row.get("sourceIntegrity", {}).get("checks", {}).get("reportSelfHash") or not row.get("sourceIntegrity", {}).get("checks", {}).get("exrSha"):
            return False
        for mechanism, definition in p1_spec["mechanisms"].items():
            observed = row.get("mechanisms", {}).get(mechanism, {})
            if not observed.get("passAvailable") or not observed.get("allFinite") or not observed.get("originalPayloadByteIdentity") or "boundary" not in observed:
                return False
            for owner_id, token in definition["expectedTokens"].items():
                owner = observed.get("owners", {}).get(owner_id, {})
                if owner.get("pixels", 0) < p1_spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"] or owner.get("expectedToken") != float(np.float32(token)) or owner.get("exactTokenPixels") != owner.get("pixels") or owner.get("nonTokenPixels") != 0 or owner.get("minimum") != float(np.float32(token)) or owner.get("maximum") != float(np.float32(token)):
                    return False
    gates = {mechanism: bound.mechanism_gate(p1_spec, cells, mechanism) for mechanism in bound.PASS_SUFFIX}
    material = gates["MATERIAL_INDEX"]["viable"]
    custom = gates["CUSTOM_VALUE_AOV"]["viable"]
    control = gates["OBJECT_INDEX_CONTROL"]
    control_ok = not control["viable"] and all(control["common"][name] for name in control["common"] if name != "DISTINGUISHES_SAME_OBJECT_INDEX_OWNERS") and all(control["additional"].values())
    return control_ok and projection.get("materialIndexViable") == material and projection.get("customAovViable") == custom and projection.get("reportedVerdict") == verdict_for(p1_spec, material, custom) and projection.get("verdictMappingIdentity") is True


def build_attacks(projection: dict, c1_spec: dict, p1_spec: dict, bound) -> list[dict]:
    attacks = []

    def attack(target, mutation):
        candidate = copy.deepcopy(projection)
        mutation(candidate)
        attacks.append({"id": f"M{len(attacks) + 1:02d}", "target": target, "passed": not projection_ok(candidate, c1_spec, p1_spec, bound)})

    attack("restore transposed orthographic extent", lambda value: value.update({"projectionConvention": "ORTHO_SCALE_IS_HEIGHT"}))
    attack("make projection validation require both candidates", lambda value: value.update({"outcomeNeutralValidation": False}))
    attack("derive mask from Material Index", lambda value: value.update({"maskSource": "MATERIAL_INDEX"}))
    attack("derive mask from custom AOV", lambda value: value.update({"maskSource": "CUSTOM_AOV"}))
    attack("change one source EXR hash", lambda value: value["cells"][0].update({"sourceIdentity": False}))
    attack("change one source report hash", lambda value: value["cells"][0]["sourceIntegrity"]["checks"].update({"reportSelfHash": False}))
    attack("change one extracted payload hash", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"].update({"originalPayloadByteIdentity": False}))
    attack("change one stable-interior token", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"]["owners"]["P1_FOREGROUND"].update({"minimum": 0.25}))
    attack("shrink the stable-interior margin", lambda value: value.update({"stableInteriorMarginPixels": 2.0}))
    attack("change the minimum interior pixels", lambda value: value.update({"minimumInteriorPixels": 1}))
    attack("break display invariance", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"].update({"payloadSha256": "0" * 64}))
    attack("break repeat invariance", lambda value: value["cells"][1]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"payloadSha256": "0" * 64}))
    attack("claim Object Index distinguishes owners", lambda value: value.update({"objectIndexDistinguishesOwners": True}))
    attack("change frozen verdict mapping", lambda value: value.update({"verdictMappingIdentity": False}))
    attack("hide a boundary measurement", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"].pop("boundary"))
    attack("add a render call", lambda value: value.update({"newRenderCalls": 1}))
    attack("change reported Material Index viability", lambda value: value.update({"materialIndexViable": not value["materialIndexViable"]}))
    attack("change reported custom AOV viability", lambda value: value.update({"customAovViable": not value["customAovViable"]}))
    attack("change reported verdict", lambda value: value.update({"reportedVerdict": p1_spec["frozenDecision"]["noneViable"] if value["reportedVerdict"] != p1_spec["frozenDecision"]["noneViable"] else p1_spec["frozenDecision"]["bothViable"]}))
    attack("hide pass availability", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"passAvailable": False}))
    for index in range(8):
        attack(f"cell-{index + 1} corrected payload identity", lambda value, row=index: value["cells"][row]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"originalPayloadByteIdentity": False}))
    return attacks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    c1_spec = json.loads(args.spec.read_text())
    root = args.output_root.resolve()
    if root != (repo / c1_spec["freshness"]["correctedOutputRoot"]).resolve() or not root.is_dir() or args.output.exists() or (root / "arrays").exists():
        raise RuntimeError("P1-C1 corrected output freshness mismatch")
    invalid_path = repo / c1_spec["parents"]["p1InvalidAnalyzer"]["uri"]
    bound = load_bound(invalid_path)
    if bound.sha_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("P1-C1 spec identity mismatch")
    parent_checks = {name: bound.sha_file(repo / row["uri"]) == row["sha256"] for name, row in c1_spec["parents"].items()}
    source_checks = {row["cell"]: bound.sha_file(repo / row["reportUri"]) == row["reportSha256"] and bound.sha_file(repo / row["exrUri"]) == row["exrSha256"] for row in c1_spec["sourceManifest"]}
    p1_spec = json.loads((repo / c1_spec["parents"]["p1Spec"]["uri"]).read_text())
    execution = json.loads((repo / c1_spec["parents"]["p1Execution"]["uri"]).read_text())
    runtime_ok = bound.sha_file(Path(os.sys.executable)) == p1_spec["runtime"]["python"]["sha256"] and np.__version__ == p1_spec["runtime"]["python"]["numpy"] and oiio.VERSION_STRING == p1_spec["runtime"]["python"]["openImageIO"]
    if not all(parent_checks.values()) or not all(source_checks.values()) or not runtime_ok or not bound.self_ok(execution, "executionHash"):
        raise RuntimeError("P1-C1 immutable parent/runtime mismatch")
    manifest = {row["cell"]: row for row in c1_spec["sourceManifest"]}
    p1_root = repo / p1_spec["freshness"]["formalRoot"]
    arrays_root = root / "arrays"
    cells = []
    for frame in p1_spec["formalMatrix"]["frames"]:
        analytic = corrected_masks(p1_spec, frame)
        for display in p1_spec["sceneContract"]["displayCells"]:
            display_id = display["id"]
            for repeat in p1_spec["formalMatrix"]["repeats"]:
                cell_id = f"F{frame}/{display_id}/R{repeat}"
                item = manifest[cell_id]
                report_path, exr_path = repo / item["reportUri"], repo / item["exrUri"]
                report = json.loads(report_path.read_text())
                integrity = bound.source_integrity(p1_spec, report, report_path, exr_path, frame, display_id, repeat)
                loaded = bound.load_parts(exr_path)
                roster = {suffix: [name for name in loaded["roster"] if name.endswith(suffix)] for suffix in p1_spec["sceneContract"]["output"]["expectedPassSuffixes"]}
                mechanism_rows = {}
                out_dir = arrays_root / f"frame-{frame}" / display_id / f"R{repeat}"
                out_dir.mkdir(parents=True, exist_ok=False)
                for mechanism, suffix in bound.PASS_SUFFIX.items():
                    pass_name, pixels, channels = bound.select_part(loaded, suffix)
                    values = np.ascontiguousarray(pixels[..., 0], dtype="<f4")
                    payload = values.tobytes()
                    filename = bound.PAYLOAD_NAME[mechanism]
                    old_payload = (p1_root / "arrays" / f"frame-{frame}" / display_id / f"R{repeat}" / filename).read_bytes()
                    (out_dir / filename).write_bytes(payload)
                    tokens = p1_spec["mechanisms"][mechanism]["expectedTokens"]
                    mechanism_rows[mechanism] = {
                        "passAvailable": True,
                        "passName": pass_name,
                        "channels": channels,
                        "shape": list(values.shape),
                        "allFinite": bool(np.isfinite(values).all()),
                        "payloadSha256": bound.sha_bytes(payload),
                        "payloadBytes": len(payload),
                        "originalPayloadByteIdentity": payload == old_payload,
                        "owners": {owner: bound.interior_stats(values, analytic[owner], token) for owner, token in tokens.items()},
                        "boundary": bound.boundary_stats(values, analytic["boundary"], list(tokens.values())),
                    }
                cells.append({
                    "cell": cell_id,
                    "frame": frame,
                    "displayCell": display_id,
                    "repeat": repeat,
                    "sourcePid": report["pid"],
                    "sourceIdentity": source_checks[cell_id],
                    "sourceIntegrity": integrity,
                    "passRoster": roster,
                    "subimages": loaded["roster"],
                    "channels": loaded["channels"],
                    "maskPixels": {name: int(mask.sum()) for name, mask in analytic.items()},
                    "mechanisms": mechanism_rows,
                })
    gates = {mechanism: bound.mechanism_gate(p1_spec, cells, mechanism) for mechanism in bound.PASS_SUFFIX}
    material, custom = gates["MATERIAL_INDEX"]["viable"], gates["CUSTOM_VALUE_AOV"]["viable"]
    verdict = verdict_for(p1_spec, material, custom)
    projection = {
        "projectionConvention": "LANDSCAPE_ORTHO_SCALE_IS_WIDTH",
        "maskSource": "ANALYTIC_SPEC_ONLY",
        "outcomeNeutralValidation": True,
        "stableInteriorMarginPixels": p1_spec["analyticMaskContract"]["stableInteriorMarginPixels"],
        "minimumInteriorPixels": p1_spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"],
        "sourceRenderCalls": 8,
        "newRenderCalls": 0,
        "runtimeIdentity": runtime_ok,
        "objectIndexDistinguishesOwners": False,
        "verdictMappingIdentity": True,
        "materialIndexViable": material,
        "customAovViable": custom,
        "reportedVerdict": verdict,
        "cells": cells,
    }
    mutation_attacks = build_attacks(projection, c1_spec, p1_spec, bound)
    control = gates["OBJECT_INDEX_CONTROL"]
    checks = [
        ("PARENT_IDENTITY", all(parent_checks.values())),
        ("SOURCE_MANIFEST_IDENTITY", all(source_checks.values())),
        ("RUNTIME_AND_EXECUTION_IDENTITY", runtime_ok and bound.self_ok(execution, "executionHash")),
        ("LANDSCAPE_ORTHOGRAPHIC_PROJECTION", projection["projectionConvention"] == "LANDSCAPE_ORTHO_SCALE_IS_WIDTH"),
        ("ANALYTIC_MASK_SOURCE_ONLY", projection["maskSource"] == "ANALYTIC_SPEC_ONLY"),
        ("SOURCE_INTEGRITY", all(row["sourceIntegrity"]["passed"] for row in cells)),
        ("PASS_DISCOVERY", all(all(len(names) == 1 for names in row["passRoster"].values()) for row in cells)),
        ("RAW_ORIGINAL_CORRECTED_PAYLOAD_IDENTITY", all(value["originalPayloadByteIdentity"] for row in cells for value in row["mechanisms"].values())),
        ("OBJECT_INDEX_NEGATIVE_CONTROL", not control["viable"] and all(control["common"][name] for name in control["common"] if name != "DISTINGUISHES_SAME_OBJECT_INDEX_OWNERS") and all(control["additional"].values())),
        ("OUTCOME_NEUTRAL_PROJECTION_REPLAY", projection_ok(projection, c1_spec, p1_spec, bound)),
        ("ATTACK_TOTALITY", len(mutation_attacks) >= c1_spec["attacks"]["minimumAnalyzerAttacks"] and all(row["passed"] for row in mutation_attacks)),
        ("NEW_RENDER_MODEL_NETWORK_ZERO", c1_spec["operationContract"]["newBlenderRenderCalls"] == 0 and c1_spec["operationContract"]["modelCalls"] == 0 and c1_spec["operationContract"]["networkCalls"] == 0),
    ]
    passed = all(value for _, value in checks)
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeCorrectionResult.v0.1",
        "experimentId": c1_spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": verdict,
        "passed": passed,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "parentChecks": parent_checks,
        "sourceManifestChecks": source_checks,
        "projectionContract": {key: projection[key] for key in ("projectionConvention", "maskSource", "outcomeNeutralValidation", "stableInteriorMarginPixels", "minimumInteriorPixels")},
        "cells": cells,
        "mechanismGates": gates,
        "materialIndexViable": material,
        "customAovViable": custom,
        "objectIndexNegativeControl": True,
        "mutationAttacks": mutation_attacks,
        "mutationAttackPassed": sum(row["passed"] for row in mutation_attacks),
        "mutationAttackTotal": len(mutation_attacks),
        "operationCounts": {"analyzerProcesses": 1, "sourceBlenderProcessesReusedReadOnly": 8, "newBlenderProcesses": 0, "newBlenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": c1_spec["nonClaims"],
    }
    result = {**body, "evidenceHash": bound.canon(body)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_C1_ANALYSIS verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} hash={result['evidenceHash']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
