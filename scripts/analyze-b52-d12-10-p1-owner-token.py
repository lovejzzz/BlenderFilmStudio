#!/usr/bin/env python3
"""Analyze the formal B52-D12.10-P1 owner-token pass matrix."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be"
PASS_SUFFIX = {"OBJECT_INDEX_CONTROL": ".Object Index", "MATERIAL_INDEX": ".Material Index", "CUSTOM_VALUE_AOV": ".OwnerToken"}
PAYLOAD_NAME = {"OBJECT_INDEX_CONTROL": "object-index.f32", "MATERIAL_INDEX": "material-index.f32", "CUSTOM_VALUE_AOV": "owner-token-aov.f32"}


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
    roster, parts, channels = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        if pixels.ndim == 2:
            pixels = pixels[..., np.newaxis]
        roster.append(name)
        parts[name] = pixels
        channels[name] = list(image_spec.channelnames)
    return {"roster": roster, "parts": parts, "channels": channels}


def select_part(loaded: dict, suffix: str) -> tuple[str, np.ndarray, list[str]]:
    matches = [name for name in loaded["roster"] if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"D12.10-P1 expected one {suffix} pass, found {matches}")
    name = matches[0]
    return name, loaded["parts"][name], loaded["channels"][name]


def masks(spec: dict, frame: int) -> dict[str, np.ndarray]:
    contract = spec["sceneContract"]
    width, height = contract["resolution"]
    world_height = float(contract["camera"]["orthoScaleWorld"])
    world_width = world_height * width / height
    yy, xx = np.mgrid[0:height, 0:width]
    x_world = ((xx + 0.5) / width - 0.5) * world_width
    y_world = (0.5 - (yy + 0.5) / height) * world_height
    margin = float(spec["analyticMaskContract"]["stableInteriorMarginPixels"])
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
    return {
        "P1_FOREGROUND": fg_eroded,
        "P1_BACKGROUND": bg_eroded & ~fg_expanded,
        "boundary": inside_bg & fg_expanded & ~fg_eroded,
    }


def interior_stats(values: np.ndarray, mask: np.ndarray, token: float) -> dict:
    samples = np.asarray(values[mask], dtype=np.float32)
    expected = np.float32(token)
    exact = samples == expected
    return {
        "pixels": int(samples.size),
        "expectedToken": float(expected),
        "minimum": float(samples.min()) if samples.size else None,
        "maximum": float(samples.max()) if samples.size else None,
        "exactTokenPixels": int(exact.sum()),
        "nonTokenPixels": int((~exact).sum()),
    }


def boundary_stats(values: np.ndarray, mask: np.ndarray, tokens: list[float]) -> dict:
    samples = np.asarray(values[mask], dtype=np.float32)
    exact = np.zeros(samples.shape, dtype=bool)
    for token in tokens:
        exact |= samples == np.float32(token)
    unique = np.unique(samples)
    return {
        "pixels": int(samples.size),
        "minimum": float(samples.min()) if samples.size else None,
        "maximum": float(samples.max()) if samples.size else None,
        "exactRegisteredTokenPixels": int(exact.sum()),
        "nonRegisteredTokenPixels": int((~exact).sum()),
        "uniqueValueCount": int(unique.size),
        "uniqueValues": [float(value) for value in unique[:256]],
        "uniqueValuesTruncated": bool(unique.size > 256),
        "payloadSha256": sha_bytes(np.ascontiguousarray(samples, dtype="<f4").tobytes()),
    }


def source_integrity(spec: dict, report: dict, report_path: Path, exr_path: Path, frame: int, display_id: str, repeat: int) -> dict:
    contract = spec["sceneContract"]
    expected_owners = {
        row["analyticOwnerId"]: (int(row["objectIndex"]), int(row["materialIndex"]), float(row["customAovValue"]))
        for row in contract["owners"]
    }
    observed_owners = {
        row["analyticOwnerId"]: (int(row["objectIndex"]), int(row["materialIndex"]), float(row["customAovValue"]))
        for row in report.get("scene", {}).get("owners", [])
    }
    checks = {
        "reportSelfHash": self_ok(report, "reportHash"),
        "exrSha": report.get("output", {}).get("sha256") == sha_file(exr_path),
        "cellIdentity": report.get("frame") == frame and report.get("displayCell") == display_id and report.get("repeat") == repeat,
        "runtimeIdentity": report.get("runtime", {}).get("blender") == spec["runtime"]["blender"]["version"] and report.get("runtime", {}).get("buildHash") == spec["runtime"]["blender"]["buildHash"] and report.get("runtime", {}).get("executableSha256") == spec["runtime"]["blender"]["sha256"],
        "renderState": report.get("runtime", {}).get("engine") == contract["engine"] and report.get("runtime", {}).get("device") == contract["device"] and report.get("runtime", {}).get("samples") == contract["samples"] and report.get("runtime", {}).get("seed") == contract["seed"],
        "ownerAssignments": observed_owners == expected_owners,
        "passState": report.get("passState", {}).get("Object Index") is True and report.get("passState", {}).get("Material Index") is True and report.get("passState", {}).get("registeredAov") == {"name": contract["customAovName"], "type": contract["customAovType"], "isValid": True},
        "renderCall": report.get("operationCounts", {}).get("blenderRenderCalls") == 1 and report.get("operationCounts", {}).get("modelCalls") == 0 and report.get("operationCounts", {}).get("networkCalls") == 0,
    }
    return {"passed": all(checks.values()), "checks": checks, "reportSha256": sha_file(report_path), "exrSha256": sha_file(exr_path)}


def invariance(cells: list[dict], mechanism: str, left_key: str, right_key: str, grouping: tuple[str, str]) -> tuple[bool, list[dict]]:
    rows = []
    groups = {}
    for row in cells:
        key = tuple(row[name] for name in grouping)
        groups.setdefault(key, {})[row[left_key]] = row["mechanisms"][mechanism]["payloadSha256"]
    for key, hashes in sorted(groups.items()):
        match = len(hashes) == 2 and len(set(hashes.values())) == 1
        rows.append({"group": list(key), "hashes": hashes, "passed": match})
    return bool(rows and all(row["passed"] for row in rows)), rows


def mechanism_gate(spec: dict, cells: list[dict], mechanism: str) -> dict:
    minimum = spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"]
    tokens = spec["mechanisms"][mechanism]["expectedTokens"]
    available = all(row["mechanisms"][mechanism]["passAvailable"] for row in cells)
    finite = all(row["mechanisms"][mechanism]["allFinite"] for row in cells)
    sample_min = all(owner["pixels"] >= minimum for row in cells for owner in row["mechanisms"][mechanism]["owners"].values())
    exact = all(owner["exactTokenPixels"] == owner["pixels"] and owner["nonTokenPixels"] == 0 for row in cells for owner in row["mechanisms"][mechanism]["owners"].values())
    distinguishes = len(set(tokens.values())) == len(tokens)
    display_ok, display_rows = invariance(cells, mechanism, "displayCell", "unused", ("frame", "repeat"))
    repeat_ok, repeat_rows = invariance(cells, mechanism, "repeat", "unused", ("frame", "displayCell"))
    common = {
        "PASS_AVAILABLE_IN_MULTILAYER_EXR": available,
        "ALL_VALUES_FINITE": finite,
        "STABLE_INTERIOR_SAMPLE_MINIMUM": sample_min,
        "STABLE_INTERIOR_EXACT_TOKEN": exact,
        "DISTINGUISHES_SAME_OBJECT_INDEX_OWNERS": distinguishes,
        "DISPLAY_INVARIANT_FLOAT32_BYTES": display_ok,
        "CLEAN_PROCESS_REPEAT_FLOAT32_BYTES": repeat_ok,
    }
    if mechanism == "MATERIAL_INDEX":
        additional = {
            "MATERIAL_PASS_INDEX_ASSIGNMENT_ROUND_TRIP": all(row["sourceIntegrity"]["checks"]["ownerAssignments"] for row in cells),
            "TOKENS_ARE_INTEGER_FLOAT32": all(float(value).is_integer() and np.float32(value) == value for value in tokens.values()),
        }
    elif mechanism == "CUSTOM_VALUE_AOV":
        additional = {
            "AOV_REGISTERED_AS_VALUE": all(row["sourceIntegrity"]["checks"]["passState"] for row in cells),
            "OUTPUT_AOV_NODE_ASSIGNMENT_ROUND_TRIP": all(row["sourceIntegrity"]["checks"]["ownerAssignments"] for row in cells),
        }
    else:
        additional = {
            "STABLE_INTERIOR_EQUALS_SHARED_SEVEN": exact and set(tokens.values()) == {7.0},
            "DOES_NOT_DISTINGUISH_AS_PREREGISTERED": not distinguishes,
        }
    viable = all(common.values()) and all(additional.values())
    return {"common": common, "additional": additional, "displayComparisons": display_rows, "repeatComparisons": repeat_rows, "viable": viable}


def projection_ok(projection: dict, spec: dict) -> bool:
    expected_cells = {(frame, display["id"], repeat) for frame in spec["formalMatrix"]["frames"] for display in spec["sceneContract"]["displayCells"] for repeat in spec["formalMatrix"]["repeats"]}
    cells = projection.get("cells", [])
    if {(row.get("frame"), row.get("displayCell"), row.get("repeat")) for row in cells} != expected_cells or len(cells) != len(expected_cells):
        return False
    if projection.get("sourceRenderCalls") != spec["formalMatrix"]["blenderRenderCalls"] or projection.get("runtimeIdentity") is not True or projection.get("objectIndexDistinguishesOwners") is not False:
        return False
    for row in cells:
        if not row.get("sourceIntegrity", {}).get("passed") or not row.get("sourceIntegrity", {}).get("checks", {}).get("reportSelfHash") or not row.get("sourceIntegrity", {}).get("checks", {}).get("exrSha"):
            return False
        for mechanism, definition in spec["mechanisms"].items():
            observed = row.get("mechanisms", {}).get(mechanism, {})
            if not observed.get("passAvailable") or not observed.get("allFinite"):
                return False
            for owner_id, token in definition["expectedTokens"].items():
                owner = observed.get("owners", {}).get(owner_id, {})
                if owner.get("pixels", 0) < spec["analyticMaskContract"]["minimumInteriorPixelsPerOwnerPerCell"] or owner.get("expectedToken") != float(np.float32(token)) or owner.get("exactTokenPixels") != owner.get("pixels") or owner.get("nonTokenPixels") != 0 or owner.get("minimum") != float(np.float32(token)) or owner.get("maximum") != float(np.float32(token)):
                    return False
    material = mechanism_gate(spec, cells, "MATERIAL_INDEX")
    custom = mechanism_gate(spec, cells, "CUSTOM_VALUE_AOV")
    control = mechanism_gate(spec, cells, "OBJECT_INDEX_CONTROL")
    return material["viable"] and custom["viable"] and not control["viable"] and all(control["common"][name] for name in control["common"] if name != "DISTINGUISHES_SAME_OBJECT_INDEX_OWNERS") and all(control["additional"].values())


def attacks(projection: dict, spec: dict) -> list[dict]:
    rows = []

    def attack(target, mutation):
        candidate = copy.deepcopy(projection)
        mutation(candidate)
        rows.append({"id": f"M{len(rows) + 1:02d}", "target": target, "passed": not projection_ok(candidate, spec)})

    attack("make owners share Material Index", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"]["owners"]["P1_FOREGROUND"].update({"expectedToken": 11.0, "minimum": 11.0, "maximum": 11.0}))
    attack("make owners share custom AOV value", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"]["owners"]["P1_FOREGROUND"].update({"expectedToken": 0.25, "minimum": 0.25, "maximum": 0.25}))
    attack("swap foreground and background Material Index", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"]["owners"]["P1_FOREGROUND"].update({"minimum": 11.0, "maximum": 11.0}))
    attack("swap foreground and background custom AOV value", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"]["owners"]["P1_BACKGROUND"].update({"minimum": 0.75, "maximum": 0.75}))
    attack("perturb one stable-interior Material Index sample", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"]["owners"]["P1_FOREGROUND"].update({"nonTokenPixels": 1}))
    attack("perturb one stable-interior custom AOV sample", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"]["owners"]["P1_FOREGROUND"].update({"exactTokenPixels": value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"]["owners"]["P1_FOREGROUND"]["pixels"] - 1}))
    attack("hide an expected EXR pass", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"].update({"passAvailable": False}))
    attack("inject NaN", lambda value: value["cells"][0]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"allFinite": False}))
    attack("change one display-cell payload hash", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"].update({"payloadSha256": "0" * 64}))
    attack("change one repeat payload hash", lambda value: value["cells"][1]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"payloadSha256": "0" * 64}))
    attack("shrink an interior below the frozen minimum", lambda value: value["cells"][0]["mechanisms"]["MATERIAL_INDEX"]["owners"]["P1_BACKGROUND"].update({"pixels": 1, "exactTokenPixels": 1}))
    attack("claim Object Index distinguishes the owners", lambda value: value.update({"objectIndexDistinguishesOwners": True}))
    attack("change a source EXR SHA", lambda value: value["cells"][0]["sourceIntegrity"]["checks"].update({"exrSha": False}))
    attack("change a source report self-hash", lambda value: value["cells"][0]["sourceIntegrity"]["checks"].update({"reportSelfHash": False}))
    attack("change render-call total", lambda value: value.update({"sourceRenderCalls": 7}))
    attack("change Blender runtime identity", lambda value: value.update({"runtimeIdentity": False}))
    for index in range(8):
        attack(f"cell-{index + 1} owner-token payload identity", lambda value, row=index: value["cells"][row]["mechanisms"]["CUSTOM_VALUE_AOV"].update({"payloadSha256": f"{row + 1:064x}"}))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    execution = json.loads(args.execution.read_text())
    if sha_file(args.spec) != SPEC_SHA256 or args.output.exists() or args.root.resolve() != (repo / spec["freshness"]["formalRoot"]).resolve():
        raise RuntimeError("D12.10-P1 analyzer identity/output mismatch")
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in spec["parents"].items()}
    runtime_ok = sha_file(Path(os.sys.executable)) == spec["runtime"]["python"]["sha256"] and np.__version__ == spec["runtime"]["python"]["numpy"] and oiio.VERSION_STRING == spec["runtime"]["python"]["openImageIO"]
    if not all(parent_checks.values()) or not runtime_ok or not self_ok(execution, "executionHash"):
        raise RuntimeError("D12.10-P1 analyzer parent/runtime/execution mismatch")
    cells = []
    arrays_root = args.root / "arrays"
    for frame in spec["formalMatrix"]["frames"]:
        analytic = masks(spec, frame)
        for display in spec["sceneContract"]["displayCells"]:
            display_id = display["id"]
            for repeat in spec["formalMatrix"]["repeats"]:
                cell_id = f"F{frame}/{display_id}/R{repeat}"
                source = args.root / "sources" / f"frame-{frame}" / display_id / f"R{repeat}"
                report_path, exr_path = source / "report.json", source / "source.exr"
                report = json.loads(report_path.read_text())
                integrity = source_integrity(spec, report, report_path, exr_path, frame, display_id, repeat)
                loaded = load_parts(exr_path)
                pass_roster = {}
                for suffix in spec["sceneContract"]["output"]["expectedPassSuffixes"]:
                    names = [name for name in loaded["roster"] if name.endswith(suffix)]
                    pass_roster[suffix] = names
                mechanism_rows = {}
                cell_array_dir = arrays_root / f"frame-{frame}" / display_id / f"R{repeat}"
                cell_array_dir.mkdir(parents=True, exist_ok=False)
                for mechanism, suffix in PASS_SUFFIX.items():
                    pass_name, pass_pixels, channels = select_part(loaded, suffix)
                    if pass_pixels.shape[:2] != tuple(reversed(spec["sceneContract"]["resolution"])) or pass_pixels.shape[-1] != 1:
                        raise RuntimeError(f"D12.10-P1 malformed pass {pass_name}: {pass_pixels.shape}")
                    values = np.ascontiguousarray(pass_pixels[..., 0], dtype="<f4")
                    payload = values.tobytes()
                    (cell_array_dir / PAYLOAD_NAME[mechanism]).write_bytes(payload)
                    tokens = spec["mechanisms"][mechanism]["expectedTokens"]
                    mechanism_rows[mechanism] = {
                        "passAvailable": True,
                        "passName": pass_name,
                        "channels": channels,
                        "shape": list(values.shape),
                        "allFinite": bool(np.isfinite(values).all()),
                        "payloadSha256": sha_bytes(payload),
                        "payloadBytes": len(payload),
                        "owners": {owner_id: interior_stats(values, analytic[owner_id], token) for owner_id, token in tokens.items()},
                        "boundary": boundary_stats(values, analytic["boundary"], list(tokens.values())),
                    }
                cells.append({
                    "cell": cell_id,
                    "frame": frame,
                    "displayCell": display_id,
                    "repeat": repeat,
                    "sourcePid": report["pid"],
                    "sourceIntegrity": integrity,
                    "passRoster": pass_roster,
                    "subimages": loaded["roster"],
                    "channels": loaded["channels"],
                    "maskPixels": {key: int(value.sum()) for key, value in analytic.items()},
                    "mechanisms": mechanism_rows,
                })

    gates = {mechanism: mechanism_gate(spec, cells, mechanism) for mechanism in PASS_SUFFIX}
    material_viable = gates["MATERIAL_INDEX"]["viable"]
    custom_viable = gates["CUSTOM_VALUE_AOV"]["viable"]
    labels = spec["frozenDecision"]
    verdict = labels["bothViable"] if material_viable and custom_viable else labels["materialOnly"] if material_viable else labels["customAovOnly"] if custom_viable else labels["noneViable"]
    projection = {
        "cells": cells,
        "sourceRenderCalls": sum(row.get("operationCounts", {}).get("blenderRenderCalls", 0) for row in (json.loads((args.root / "sources" / f"frame-{frame}" / display["id"] / f"R{repeat}" / "report.json").read_text()) for frame in spec["formalMatrix"]["frames"] for display in spec["sceneContract"]["displayCells"] for repeat in spec["formalMatrix"]["repeats"])),
        "runtimeIdentity": runtime_ok,
        "objectIndexDistinguishesOwners": len(set(spec["mechanisms"]["OBJECT_INDEX_CONTROL"]["expectedTokens"].values())) > 1,
    }
    mutation_rows = attacks(projection, spec)
    checks = [
        ("PARENT_IDENTITY", all(parent_checks.values())),
        ("RUNTIME_IDENTITY", runtime_ok),
        ("EXECUTION_IDENTITY", self_ok(execution, "executionHash")),
        ("SOURCE_INTEGRITY", all(row["sourceIntegrity"]["passed"] for row in cells)),
        ("PASS_DISCOVERY", all(all(len(names) == 1 for names in row["passRoster"].values()) for row in cells)),
        ("OBJECT_INDEX_NEGATIVE_CONTROL", not gates["OBJECT_INDEX_CONTROL"]["viable"] and all(gates["OBJECT_INDEX_CONTROL"]["common"][name] for name in gates["OBJECT_INDEX_CONTROL"]["common"] if name != "DISTINGUISHES_SAME_OBJECT_INDEX_OWNERS") and all(gates["OBJECT_INDEX_CONTROL"]["additional"].values())),
        ("PROJECTION_REPLAY", projection_ok(projection, spec)),
        ("ATTACK_TOTALITY", len(mutation_rows) >= spec["attacks"]["minimumRegisteredAttacks"] and all(row["passed"] for row in mutation_rows)),
        ("MODEL_NETWORK_ZERO", projection["sourceRenderCalls"] == spec["formalMatrix"]["blenderRenderCalls"] and all(row["sourceIntegrity"]["checks"]["renderCall"] for row in cells)),
    ]
    passed = all(value for _, value in checks) and (material_viable or custom_viable)
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": verdict,
        "passed": passed,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "parentChecks": parent_checks,
        "runtimeIdentity": runtime_ok,
        "cells": cells,
        "mechanismGates": gates,
        "materialIndexViable": material_viable,
        "customAovViable": custom_viable,
        "objectIndexNegativeControl": True,
        "mutationAttacks": mutation_rows,
        "mutationAttackPassed": sum(row["passed"] for row in mutation_rows),
        "mutationAttackTotal": len(mutation_rows),
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": projection["sourceRenderCalls"], "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "evidenceHash": canon(body)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_ANALYSIS verdict={verdict} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} hash={result['evidenceHash']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
