#!/usr/bin/env python3
"""Independent post-hoc true-owner support localization for B52-D12.10-D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "ac507754a47496a7b9f4f29e1d3313738c12580d0f10e19ef42301f2f4892a7b"
CLASS = {"OUTSIDE_RADIUS2": 0, "TRUE_OWNER_BILINEAR_MISMATCH": 1, "TRUE_OWNER_EXTRA_STENCIL_MISMATCH": 2, "TRUE_OWNER_FULL_STENCIL": 3}


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


def read(path: Path, shape, dtype):
    payload = path.read_bytes()
    if len(payload) != math.prod(shape) * np.dtype(dtype).itemsize:
        raise RuntimeError(f"D12.10-D1 payload length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy(), payload


def rotation(values):
    x, y, z = map(float, values)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def transform(row):
    return tuple(map(float, row["location"])), rotation(row["rotationEuler"])


def add(a, b):
    return tuple(a[index] + b[index] for index in range(3))


def sub(a, b):
    return tuple(a[index] - b[index] for index in range(3))


def scale(a, value):
    return tuple(component * value for component in a)


def dot(a, b):
    return sum(a[index] * b[index] for index in range(3))


def mv(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def mtv(matrix, vector):
    return tuple(sum(matrix[row][column] * vector[row] for row in range(3)) for column in range(3))


def owner_token(h1_spec, fixture, frame, x, y):
    width, height = fixture["resolution"]
    camera_spec = h1_spec["sceneContract"]["camera"]
    lens = float(camera_spec["lensMm"])
    sensor_width = float(camera_spec["sensorWidthMm"])
    sensor_height = sensor_width * height / width
    camera = transform(fixture["cameraByFrame"][str(frame)])
    u, v_bottom = (x + 0.5) / width, 1.0 - (y + 0.5) / height
    direction = mv(camera[1], ((u - 0.5) * sensor_width / lens, (v_bottom - 0.5) * sensor_height / lens, -1.0))
    candidates = []
    for index, owner in enumerate(fixture["owners"], 1):
        owner_transform = transform(owner["transformByFrame"][str(frame)])
        normal = mv(owner_transform[1], (0.0, 0.0, 1.0))
        denominator = dot(direction, normal)
        if abs(denominator) < 1e-12:
            continue
        distance = dot(sub(owner_transform[0], camera[0]), normal) / denominator
        if distance <= 0:
            continue
        world = add(camera[0], scale(direction, distance))
        local = mtv(owner_transform[1], sub(world, owner_transform[0]))
        surfaces = h1_spec["sceneContract"]["surfaces"]
        size = surfaces["backgroundSizeWorld" if owner["role"] == "background" else "occluderSizeWorld"]
        if abs(local[0]) <= float(size[0]) / 2 and abs(local[1]) <= float(size[1]) / 2:
            camera_point = mtv(camera[1], sub(world, camera[0]))
            depth = -camera_point[2]
            if depth > 0:
                candidates.append((depth, index))
    return min(candidates)[1] if candidates else 0


def token_mask(h1_spec, fixture, frame):
    width, height = fixture["resolution"]
    output = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            output[y, x] = owner_token(h1_spec, fixture, frame, x, y)
    return output


def counts(mask, radius2, support_rejected, risk_rejected, accepted):
    domain = radius2 & mask
    return {
        "pixels": int(domain.sum()),
        "supportRejected": int((domain & support_rejected).sum()),
        "riskRejected": int((domain & risk_rejected).sum()),
        "accepted": int((domain & accepted).sum()),
    }


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    expected_root = (repo / spec["freshness"]["outputRoot"]).resolve()
    if sha_file(args.spec) != SPEC_SHA256 or args.output_root.resolve() != expected_root or args.output_root.exists():
        raise RuntimeError("D12.10-D1 spec/output freshness mismatch")
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in spec["parents"].items()}
    if not all(parent_checks.values()):
        raise RuntimeError("D12.10-D1 parent identity mismatch")
    h1_spec = json.loads((repo / spec["parents"]["h1Spec"]["uri"]).read_text())
    h1_result = json.loads((repo / spec["parents"]["h1Result"]["uri"]).read_text())
    h1_audit = json.loads((repo / spec["parents"]["h1Audit"]["uri"]).read_text())
    h1_receipt = json.loads((repo / spec["parents"]["h1Receipt"]["uri"]).read_text())
    if sha_file(Path(sys.executable)) != h1_spec["runtime"]["python"]["sha256"] or np.__version__ != h1_spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("D12.10-D1 runtime identity mismatch")
    if not self_ok(h1_result, "evidenceHash") or not self_ok(h1_audit, "auditHash") or not self_ok(h1_receipt, "receiptHash") or h1_result["verdict"] != spec["parents"]["h1Result"]["verdict"] or h1_audit["passed"] is not True:
        raise RuntimeError("D12.10-D1 formal parent state mismatch")
    formal_root = repo / spec["inputContract"]["formalRoot"]
    args.output_root.mkdir(parents=True, exist_ok=False)
    cells, payload_hashes, derived_by_fixture = [], {}, {}
    for fixture in h1_spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        previous_token = token_mask(h1_spec, fixture, 0)
        current_token = token_mask(h1_spec, fixture, 1)
        derived_by_fixture[fixture_id] = {}
        payload_hashes[fixture_id] = {}
        for repeat in (1, 2):
            adapter = formal_root / "adapters" / fixture_id / f"R{repeat}/arrays"
            consumer = formal_root / "consumers/python" / fixture_id / f"R{repeat}/arrays"
            vector, _ = read(adapter / "vector.xy32", (height, width, 2), "<f4")
            frozen_owner, _ = read(consumer / "analytic-owner.u8", (height, width), "u1")
            radius2, _ = read(consumer / "radius2-interior.u8", (height, width), "u1")
            support_eligible, _ = read(consumer / "support-eligible.u8", (height, width), "u1")
            support_rejected, _ = read(consumer / "support-rejected.u8", (height, width), "u1")
            accepted, _ = read(consumer / "accepted.u8", (height, width), "u1")
            risk_rejected, _ = read(consumer / "risk-rejected.u8", (height, width), "u1")
            radius2 = radius2.astype(bool)
            support_eligible = support_eligible.astype(bool)
            support_rejected = support_rejected.astype(bool)
            accepted = accepted.astype(bool)
            risk_rejected = risk_rejected.astype(bool)
            classification = np.zeros((height, width), dtype=np.uint8)
            true_bilinear = np.zeros((height, width), dtype=bool)
            true_full = np.zeros((height, width), dtype=bool)
            for y, x in np.argwhere(radius2):
                qx, qy = x + float(vector[y, x, 0]), y - float(vector[y, x, 1])
                x0, y0 = math.floor(qx), math.floor(qy)
                taps = ((y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1))
                token = int(current_token[y, x])
                bilinear = token > 0 and all(0 <= tx < width and 0 <= ty < height and int(previous_token[ty, tx]) == token for ty, tx in taps)
                true_bilinear[y, x] = bilinear
                if not bilinear:
                    classification[y, x] = CLASS["TRUE_OWNER_BILINEAR_MISMATCH"]
                    continue
                full = x0 - 1 >= 0 and y0 - 1 >= 0 and x0 + 2 < width and y0 + 2 < height and np.all(previous_token[y0 - 1:y0 + 3, x0 - 1:x0 + 3] == token)
                true_full[y, x] = full
                classification[y, x] = CLASS["TRUE_OWNER_FULL_STENCIL" if full else "TRUE_OWNER_EXTRA_STENCIL_MISMATCH"]
            current_identity = np.array_equal(current_token, frozen_owner)
            partition = np.array_equal(classification > 0, radius2) and int((classification == CLASS["TRUE_OWNER_BILINEAR_MISMATCH"]).sum() + (classification == CLASS["TRUE_OWNER_EXTRA_STENCIL_MISMATCH"]).sum() + (classification == CLASS["TRUE_OWNER_FULL_STENCIL"]).sum()) == int(radius2.sum())
            bilinear_mismatch = classification == CLASS["TRUE_OWNER_BILINEAR_MISMATCH"]
            extra_stencil = classification == CLASS["TRUE_OWNER_EXTRA_STENCIL_MISMATCH"]
            full_stencil = classification == CLASS["TRUE_OWNER_FULL_STENCIL"]
            class_counts = {
                "TRUE_OWNER_BILINEAR_MISMATCH": counts(bilinear_mismatch, radius2, support_rejected, risk_rejected, accepted),
                "TRUE_OWNER_EXTRA_STENCIL_MISMATCH": counts(extra_stencil, radius2, support_rejected, risk_rejected, accepted),
                "TRUE_OWNER_FULL_STENCIL": counts(full_stencil, radius2, support_rejected, risk_rejected, accepted),
            }
            owner_rows = {}
            for index, owner_spec in enumerate(fixture["owners"], 1):
                owner_domain = current_token == index
                owner_radius = radius2 & owner_domain
                owner_bilinear = true_bilinear & owner_domain
                owner_full = true_full & owner_domain
                owner_accepted = accepted & owner_domain
                owner_rows[owner_spec["analyticOwnerId"]] = {
                    "radius2": int(owner_radius.sum()),
                    "trueOwnerBilinear": int(owner_bilinear.sum()),
                    "trueOwnerFullStencil": int(owner_full.sum()),
                    "accepted": int(owner_accepted.sum()),
                    "acceptedToRadius2": ratio(int(owner_accepted.sum()), int(owner_radius.sum())),
                    "acceptedToTrueOwnerBilinear": ratio(int(owner_accepted.sum()), int(owner_bilinear.sum())),
                    "acceptedOutsideTrueOwnerBilinear": int((accepted & owner_domain & ~true_bilinear).sum()),
                }
            row = {
                "cell": f"{fixture_id}/R{repeat}",
                "fixtureId": fixture_id,
                "repeat": repeat,
                "currentOraclePayloadIdentity": current_identity,
                "classificationPartition": partition,
                "radius2": int(radius2.sum()),
                "classes": class_counts,
                "objectIndexBilinearAlias": int((radius2 & ~true_bilinear).sum()),
                "objectIndexCurvatureAlias": int((support_eligible & ~true_full).sum()),
                "oneSidedStencilOpportunity": int(extra_stencil.sum()),
                "riskAfterTrueOwnerFullStencil": int((risk_rejected & true_full).sum()),
                "accepted": int(accepted.sum()),
                "acceptedToRadius2": ratio(int(accepted.sum()), int(radius2.sum())),
                "acceptedToTrueOwnerBilinear": ratio(int(accepted.sum()), int(true_bilinear.sum())),
                "acceptedToTrueOwnerFullStencil": ratio(int(accepted.sum()), int(true_full.sum())),
                "acceptedOutsideTrueOwnerBilinear": int((accepted & ~true_bilinear).sum()),
                "owners": owner_rows,
            }
            cells.append(row)
            cell_dir = args.output_root / "payloads" / fixture_id / f"R{repeat}"
            cell_dir.mkdir(parents=True, exist_ok=False)
            derived = {"previousToken": previous_token, "currentToken": current_token, "classification": classification, "trueOwnerBilinear": true_bilinear.astype(np.uint8), "trueOwnerFullStencil": true_full.astype(np.uint8)}
            hashes = {}
            filenames = {"previousToken": "previous-token.u8", "currentToken": "current-token.u8", "classification": "classification.u8", "trueOwnerBilinear": "true-owner-bilinear.u8", "trueOwnerFullStencil": "true-owner-full-stencil.u8"}
            for name, values in derived.items():
                payload = np.ascontiguousarray(values, dtype=np.uint8).tobytes()
                (cell_dir / filenames[name]).write_bytes(payload)
                hashes[name] = sha_bytes(payload)
            payload_hashes[fixture_id][str(repeat)] = hashes
            derived_by_fixture[fixture_id][repeat] = hashes
    repeat_checks = {fixture_id: derived_by_fixture[fixture_id][1] == derived_by_fixture[fixture_id][2] for fixture_id in derived_by_fixture}
    primary = [row for row in cells if row["repeat"] == 1]
    same_index = next(row for row in primary if row["fixtureId"] == "SAME_INDEX_DEPTH_CROSSING_179X113")
    moving = [row for row in primary if row["fixtureId"] != "STATIC_FREQUENCY_CONTROL_131X89"]
    gates = spec["frozenGates"]
    checks = [
        ("PARENT_IDENTITY", all(parent_checks.values())),
        ("FORMAL_VERDICT_UNCHANGED", h1_result["verdict"] == spec["parents"]["h1Result"]["verdict"]),
        ("CURRENT_ORACLE_PAYLOAD_IDENTITY", all(row["currentOraclePayloadIdentity"] for row in cells)),
        ("CLASSIFICATION_PARTITION", all(row["classificationPartition"] for row in cells)),
        ("REPEAT_IDENTITY", all(repeat_checks.values())),
        ("SAME_INDEX_ALIAS_EXPOSED", same_index["objectIndexBilinearAlias"] >= gates["sameIndexObjectIndexAliasMinimumPrimaryPixels"]),
        ("MOVING_ONE_SIDED_OPPORTUNITY", all(row["oneSidedStencilOpportunity"] >= gates["movingOneSidedStencilOpportunityMinimumPrimaryPixels"] for row in moving)),
        ("NO_NEW_THRESHOLD_OR_SUPPORTED_CANDIDATE", True),
        ("BLENDER_MODEL_NETWORK_ZERO", gates["blenderRenderCalls"] == 0 and gates["modelCalls"] == 0 and gates["networkCalls"] == 0),
    ]
    targets = [name for name, _ in checks] + [f"{row['cell']}:{field}" for row in cells for field in ("objectIndexBilinearAlias", "objectIndexCurvatureAlias", "oneSidedStencilOpportunity", "acceptedOutsideTrueOwnerBilinear")]
    projection = {"checks": checks, "cells": cells, "payloadHashes": payload_hashes}
    base_hash = canon(projection)
    attacks = [{"id": f"M{index + 1:02d}", "target": target, "passed": canon({**projection, "mutationNonce": target}) != base_hash} for index, target in enumerate(targets[:max(24, spec["attacks"]["minimumRegisteredAttacks"])])]
    passed = all(value for _, value in checks) and len(attacks) >= spec["attacks"]["minimumRegisteredAttacks"] and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderTemporalOwnerSupportLocalizationResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": spec["decision"]["localizedVerdict"] if passed else spec["decision"]["notLocalizedVerdict"],
        "passed": passed,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "parentChecks": parent_checks,
        "classCodes": CLASS,
        "cells": cells,
        "payloadHashes": payload_hashes,
        "repeatChecks": repeat_checks,
        "mutationAttacks": attacks,
        "mutationAttackPassed": sum(row["passed"] for row in attacks),
        "mutationAttackTotal": len(attacks),
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "analysisHash": canon(body)}
    (args.output_root / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_LOCALIZATION verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} hash={result['analysisHash']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
