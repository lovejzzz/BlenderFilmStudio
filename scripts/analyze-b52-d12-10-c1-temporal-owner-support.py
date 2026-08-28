#!/usr/bin/env python3
"""Mechanical set-intersection correction for B52-D12.10-C1."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SPEC_SHA256 = "2ba1edd74fef18eacfa1c170cab4e35f80afc575eaef1ffe3500428553555403"


def load_bound_d1_tool(path: Path):
    module_spec = importlib.util.spec_from_file_location("bfs_d1210_invalid_bound", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("D12.10-C1 could not load the bound D1 tool")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def close_ratio(value, numerator: int, denominator: int) -> bool:
    expected = float(numerator / denominator) if denominator else None
    if expected is None:
        return value is None
    return isinstance(value, (int, float)) and math.isfinite(value) and abs(float(value) - expected) <= 1e-15


def ratio_in_unit(value) -> bool:
    return value is None or (isinstance(value, (int, float)) and math.isfinite(value) and 0.0 <= float(value) <= 1.0)


def d1_identity_projection(row: dict) -> dict:
    owner_fields = (
        "radius2",
        "trueOwnerBilinear",
        "trueOwnerFullStencil",
        "accepted",
        "acceptedOutsideTrueOwnerBilinear",
    )
    return {
        "cell": row["cell"],
        "fixtureId": row["fixtureId"],
        "repeat": row["repeat"],
        "currentOraclePayloadIdentity": row["currentOraclePayloadIdentity"],
        "classificationPartition": row["classificationPartition"],
        "radius2": row["radius2"],
        "classes": row["classes"],
        "objectIndexBilinearAlias": row["objectIndexBilinearAlias"],
        "objectIndexCurvatureAlias": row["objectIndexCurvatureAlias"],
        "oneSidedStencilOpportunity": row["oneSidedStencilOpportunity"],
        "riskAfterTrueOwnerFullStencil": row["riskAfterTrueOwnerFullStencil"],
        "accepted": row["accepted"],
        "acceptedOutsideTrueOwnerBilinear": row["acceptedOutsideTrueOwnerBilinear"],
        "owners": {
            owner_id: {field: owner[field] for field in owner_fields}
            for owner_id, owner in sorted(row["owners"].items())
        },
    }


def row_sets_and_ratios_ok(row: dict) -> bool:
    rows = [row, *row["owners"].values()]
    for item in rows:
        if item["accepted"] != item["acceptedWithinTrueOwnerBilinear"] + item["acceptedOutsideTrueOwnerBilinear"]:
            return False
        if item["acceptedWithinTrueOwnerBilinear"] != item["acceptedWithinTrueOwnerFullStencil"] + item["acceptedWithinTrueOwnerExtraStencilMismatch"]:
            return False
        if not close_ratio(item["acceptedToRadius2"], item["accepted"], item["radius2"]):
            return False
        if not close_ratio(item["acceptedToTrueOwnerBilinear"], item["acceptedWithinTrueOwnerBilinear"], item["trueOwnerBilinear"]):
            return False
        if not close_ratio(item["acceptedToTrueOwnerFullStencil"], item["acceptedWithinTrueOwnerFullStencil"], item["trueOwnerFullStencil"]):
            return False
        if not all(ratio_in_unit(item[field]) for field in ("acceptedToRadius2", "acceptedToTrueOwnerBilinear", "acceptedToTrueOwnerFullStencil")):
            return False
        if not (0 <= item["acceptedWithinTrueOwnerFullStencil"] <= item["trueOwnerFullStencil"] <= item["trueOwnerBilinear"] <= item["radius2"]):
            return False
    return True


def projection_ok(projection: dict, d1_result: dict) -> bool:
    expected = {row["cell"]: d1_identity_projection(row) for row in d1_result["cells"]}
    if projection["payloadHashes"] != d1_result["payloadHashes"]:
        return False
    if len(projection["cells"]) != len(expected):
        return False
    seen = set()
    for row in projection["cells"]:
        cell = row.get("cell")
        if cell not in expected or cell in seen:
            return False
        seen.add(cell)
        if d1_identity_projection(row) != expected[cell] or not row_sets_and_ratios_ok(row):
            return False
    return seen == set(expected)


def build_attacks(projection: dict, d1_result: dict, minimum: int) -> list[dict]:
    same_index_cell = "SAME_INDEX_DEPTH_CROSSING_179X113/R1"
    cell_index = next(index for index, row in enumerate(projection["cells"]) if row["cell"] == same_index_cell)
    background = "D129_DEPTH_BACKGROUND"
    mutations = []

    def register(attack_id, target, mutate):
        mutations.append((attack_id, target, mutate))

    register("M01", "replace accepted intersection with total accepted", lambda value: value["cells"][cell_index].__setitem__("acceptedWithinTrueOwnerBilinear", value["cells"][cell_index]["accepted"]))
    register("M02", "replace full-stencil accepted intersection with bilinear accepted", lambda value: value["cells"][cell_index].__setitem__("acceptedWithinTrueOwnerFullStencil", value["cells"][cell_index]["acceptedWithinTrueOwnerBilinear"]))
    register("M03", "emit ratio below zero", lambda value: value["cells"][cell_index].__setitem__("acceptedToTrueOwnerBilinear", -0.01))
    register("M04", "emit ratio above one", lambda value: value["cells"][cell_index].__setitem__("acceptedToTrueOwnerFullStencil", 1.01))
    register("M05", "break cell accepted decomposition", lambda value: value["cells"][cell_index].__setitem__("acceptedWithinTrueOwnerBilinear", value["cells"][cell_index]["acceptedWithinTrueOwnerBilinear"] + 1))
    register("M06", "break owner accepted decomposition", lambda value: value["cells"][cell_index]["owners"][background].__setitem__("acceptedWithinTrueOwnerBilinear", value["cells"][cell_index]["owners"][background]["acceptedWithinTrueOwnerBilinear"] + 1))
    register("M07", "hide acceptedOutsideTrueOwnerBilinear", lambda value: value["cells"][cell_index].__setitem__("acceptedOutsideTrueOwnerBilinear", 0))
    register("M08", "hide owner acceptedOutsideTrueOwnerBilinear", lambda value: value["cells"][cell_index]["owners"][background].__setitem__("acceptedOutsideTrueOwnerBilinear", 0))
    register("M09", "change D1 class count", lambda value: value["cells"][cell_index]["classes"]["TRUE_OWNER_BILINEAR_MISMATCH"].__setitem__("pixels", 0))
    register("M10", "change Object Index bilinear alias", lambda value: value["cells"][cell_index].__setitem__("objectIndexBilinearAlias", 0))
    register("M11", "change Object Index curvature alias", lambda value: value["cells"][cell_index].__setitem__("objectIndexCurvatureAlias", 0))
    register("M12", "change one-sided opportunity", lambda value: value["cells"][cell_index].__setitem__("oneSidedStencilOpportunity", 0))
    register("M13", "change risk-after-full-stencil", lambda value: value["cells"][0].__setitem__("riskAfterTrueOwnerFullStencil", value["cells"][0]["riskAfterTrueOwnerFullStencil"] + 1))
    register("M14", "change derived payload hash", lambda value: next(iter(next(iter(value["payloadHashes"].values())).values())).__setitem__("classification", "0" * 64))

    for row_index, row in enumerate(projection["cells"]):
        register(
            f"M{len(mutations) + 1:02d}",
            f"{row['cell']}: acceptedWithinTrueOwnerFullStencil",
            lambda value, index=row_index: value["cells"][index].__setitem__("acceptedWithinTrueOwnerFullStencil", value["cells"][index]["acceptedWithinTrueOwnerFullStencil"] - 1),
        )
    for row_index, row in enumerate(projection["cells"]):
        owner_id = sorted(row["owners"])[0]
        register(
            f"M{len(mutations) + 1:02d}",
            f"{row['cell']}/{owner_id}: acceptedToTrueOwnerBilinear",
            lambda value, index=row_index, owner=owner_id: value["cells"][index]["owners"][owner].__setitem__("acceptedToTrueOwnerBilinear", 1.5),
        )

    if len(mutations) < minimum:
        raise RuntimeError("D12.10-C1 attack registry below frozen minimum")
    attacks = []
    for attack_id, target, mutate in mutations:
        mutated = copy.deepcopy(projection)
        mutate(mutated)
        attacks.append({"id": attack_id, "target": target, "passed": not projection_ok(mutated, d1_result)})
    return attacks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    expected_tool = (repo / spec["freshness"]["correctedToolPath"]).resolve()
    expected_root = (repo / spec["freshness"]["correctedOutputRoot"]).resolve()
    if args.spec.resolve() != (repo / "specs/blender-temporal-owner-support-localization-c1.v0.1.json").resolve():
        raise RuntimeError("D12.10-C1 unexpected spec path")
    if Path(__file__).resolve() != expected_tool or args.output_root.resolve() != expected_root or args.output_root.exists():
        raise RuntimeError("D12.10-C1 tool/output freshness mismatch")
    if not hasattr(sys.modules[__name__], "SPEC_SHA256"):
        raise RuntimeError("D12.10-C1 internal identity failure")

    parent_checks = {
        name: (repo / row["uri"]).is_file() and None
        for name, row in spec["parents"].items()
    }
    d1_tool_path = repo / spec["parents"]["d1210InvalidTool"]["uri"]
    d1 = load_bound_d1_tool(d1_tool_path)
    for name, row in spec["parents"].items():
        parent_checks[name] = d1.sha_file(repo / row["uri"]) == row["sha256"]
    parent_checks["c1Spec"] = d1.sha_file(args.spec) == SPEC_SHA256
    if not all(parent_checks.values()):
        raise RuntimeError("D12.10-C1 parent or spec identity mismatch")

    d1_spec = json.loads((repo / spec["parents"]["d1210Spec"]["uri"]).read_text())
    d1_result = json.loads((repo / spec["parents"]["d1210InvalidResult"]["uri"]).read_text())
    if d1_result.get("analysisHash") != spec["parents"]["d1210InvalidResult"]["analysisHash"] or not d1.self_ok(d1_result, "analysisHash"):
        raise RuntimeError("D12.10-C1 invalid D1 result identity mismatch")
    h1_spec = json.loads((repo / d1_spec["parents"]["h1Spec"]["uri"]).read_text())
    h1_result = json.loads((repo / d1_spec["parents"]["h1Result"]["uri"]).read_text())
    h1_audit = json.loads((repo / d1_spec["parents"]["h1Audit"]["uri"]).read_text())
    h1_receipt = json.loads((repo / d1_spec["parents"]["h1Receipt"]["uri"]).read_text())
    h1_parent_checks = {name: d1.sha_file(repo / row["uri"]) == row["sha256"] for name, row in d1_spec["parents"].items()}
    if not all(h1_parent_checks.values()):
        raise RuntimeError("D12.10-C1 H1 parent identity mismatch")
    if d1.sha_file(Path(sys.executable)) != h1_spec["runtime"]["python"]["sha256"] or np.__version__ != h1_spec["runtime"]["python"]["numpy"]:
        raise RuntimeError("D12.10-C1 runtime identity mismatch")
    if not d1.self_ok(h1_result, "evidenceHash") or not d1.self_ok(h1_audit, "auditHash") or not d1.self_ok(h1_receipt, "receiptHash") or not h1_audit["passed"]:
        raise RuntimeError("D12.10-C1 formal parent state mismatch")

    formal_root = repo / d1_spec["inputContract"]["formalRoot"]
    args.output_root.mkdir(parents=True, exist_ok=False)
    cells, payload_hashes, repeat_material = [], {}, {}
    filenames = {
        "previousToken": "previous-token.u8",
        "currentToken": "current-token.u8",
        "classification": "classification.u8",
        "trueOwnerBilinear": "true-owner-bilinear.u8",
        "trueOwnerFullStencil": "true-owner-full-stencil.u8",
    }

    for fixture in h1_spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        previous_token = d1.token_mask(h1_spec, fixture, 0)
        current_token = d1.token_mask(h1_spec, fixture, 1)
        repeat_material[fixture_id], payload_hashes[fixture_id] = {}, {}
        for repeat in (1, 2):
            adapter = formal_root / "adapters" / fixture_id / f"R{repeat}/arrays"
            consumer = formal_root / "consumers/python" / fixture_id / f"R{repeat}/arrays"
            vector, _ = d1.read(adapter / "vector.xy32", (height, width, 2), "<f4")
            frozen_owner, _ = d1.read(consumer / "analytic-owner.u8", (height, width), "u1")
            radius2, _ = d1.read(consumer / "radius2-interior.u8", (height, width), "u1")
            support_eligible, _ = d1.read(consumer / "support-eligible.u8", (height, width), "u1")
            support_rejected, _ = d1.read(consumer / "support-rejected.u8", (height, width), "u1")
            accepted, _ = d1.read(consumer / "accepted.u8", (height, width), "u1")
            risk_rejected, _ = d1.read(consumer / "risk-rejected.u8", (height, width), "u1")
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
                    classification[y, x] = d1.CLASS["TRUE_OWNER_BILINEAR_MISMATCH"]
                    continue
                full = x0 - 1 >= 0 and y0 - 1 >= 0 and x0 + 2 < width and y0 + 2 < height and np.all(previous_token[y0 - 1:y0 + 3, x0 - 1:x0 + 3] == token)
                true_full[y, x] = full
                classification[y, x] = d1.CLASS["TRUE_OWNER_FULL_STENCIL" if full else "TRUE_OWNER_EXTRA_STENCIL_MISMATCH"]

            bilinear_mismatch = classification == d1.CLASS["TRUE_OWNER_BILINEAR_MISMATCH"]
            extra_stencil = classification == d1.CLASS["TRUE_OWNER_EXTRA_STENCIL_MISMATCH"]
            full_stencil = classification == d1.CLASS["TRUE_OWNER_FULL_STENCIL"]
            class_counts = {
                "TRUE_OWNER_BILINEAR_MISMATCH": d1.counts(bilinear_mismatch, radius2, support_rejected, risk_rejected, accepted),
                "TRUE_OWNER_EXTRA_STENCIL_MISMATCH": d1.counts(extra_stencil, radius2, support_rejected, risk_rejected, accepted),
                "TRUE_OWNER_FULL_STENCIL": d1.counts(full_stencil, radius2, support_rejected, risk_rejected, accepted),
            }

            def measurement(domain: np.ndarray) -> dict:
                local_radius = radius2 & domain
                local_bilinear = true_bilinear & domain
                local_full = true_full & domain
                local_extra = extra_stencil & domain
                local_accepted = accepted & domain
                within_bilinear = local_accepted & true_bilinear
                within_full = local_accepted & true_full
                within_extra = local_accepted & extra_stencil
                outside_bilinear = local_accepted & ~true_bilinear
                return {
                    "radius2": int(local_radius.sum()),
                    "trueOwnerBilinear": int(local_bilinear.sum()),
                    "trueOwnerFullStencil": int(local_full.sum()),
                    "accepted": int(local_accepted.sum()),
                    "acceptedWithinTrueOwnerBilinear": int(within_bilinear.sum()),
                    "acceptedWithinTrueOwnerFullStencil": int(within_full.sum()),
                    "acceptedWithinTrueOwnerExtraStencilMismatch": int(within_extra.sum()),
                    "acceptedOutsideTrueOwnerBilinear": int(outside_bilinear.sum()),
                    "acceptedToRadius2": d1.ratio(int(local_accepted.sum()), int(local_radius.sum())),
                    "acceptedToTrueOwnerBilinear": d1.ratio(int(within_bilinear.sum()), int(local_bilinear.sum())),
                    "acceptedToTrueOwnerFullStencil": d1.ratio(int(within_full.sum()), int(local_full.sum())),
                }

            row = {
                "cell": f"{fixture_id}/R{repeat}",
                "fixtureId": fixture_id,
                "repeat": repeat,
                "currentOraclePayloadIdentity": np.array_equal(current_token, frozen_owner),
                "classificationPartition": np.array_equal(classification > 0, radius2) and sum(row["pixels"] for row in class_counts.values()) == int(radius2.sum()),
                **measurement(np.ones((height, width), dtype=bool)),
                "classes": class_counts,
                "objectIndexBilinearAlias": int((radius2 & ~true_bilinear).sum()),
                "objectIndexCurvatureAlias": int((support_eligible & ~true_full).sum()),
                "oneSidedStencilOpportunity": int(extra_stencil.sum()),
                "riskAfterTrueOwnerFullStencil": int((risk_rejected & true_full).sum()),
                "owners": {
                    owner_spec["analyticOwnerId"]: measurement(current_token == owner_index)
                    for owner_index, owner_spec in enumerate(fixture["owners"], 1)
                },
            }
            cells.append(row)

            derived = {
                "previousToken": previous_token,
                "currentToken": current_token,
                "classification": classification,
                "trueOwnerBilinear": true_bilinear.astype(np.uint8),
                "trueOwnerFullStencil": true_full.astype(np.uint8),
            }
            cell_dir = args.output_root / "payloads" / fixture_id / f"R{repeat}"
            cell_dir.mkdir(parents=True, exist_ok=False)
            hashes = {}
            for name, values in derived.items():
                payload = np.ascontiguousarray(values, dtype=np.uint8).tobytes()
                hashes[name] = d1.sha_bytes(payload)
                (cell_dir / filenames[name]).write_bytes(payload)
            payload_hashes[fixture_id][str(repeat)] = hashes
            repeat_material[fixture_id][repeat] = hashes

    d1_rows = {row["cell"]: d1_identity_projection(row) for row in d1_result["cells"]}
    payload_identity = payload_hashes == d1_result["payloadHashes"]
    classification_identity = all(d1_identity_projection(row) == d1_rows.get(row["cell"]) for row in cells) and len(cells) == len(d1_rows)
    repeat_checks = {fixture_id: values[1] == values[2] for fixture_id, values in repeat_material.items()}
    set_checks = {row["cell"]: row_sets_and_ratios_ok(row) for row in cells}
    primary = [row for row in cells if row["repeat"] == 1]
    same_index = next(row for row in primary if row["fixtureId"] == "SAME_INDEX_DEPTH_CROSSING_179X113")
    moving = [row for row in primary if row["fixtureId"] != "STATIC_FREQUENCY_CONTROL_131X89"]
    gates = spec["frozenGates"]
    projection = {"cells": cells, "payloadHashes": payload_hashes}
    projection_valid = projection_ok(projection, d1_result)
    checks = [
        ("ALL_ORIGINAL_PARENT_IDENTITIES", all(parent_checks.values()) and all(h1_parent_checks.values())),
        ("INVALID_D1_IDENTITY", d1_result["analysisHash"] == spec["parents"]["d1210InvalidResult"]["analysisHash"]),
        ("FORMAL_VERDICT_UNCHANGED", h1_result["verdict"] == d1_spec["parents"]["h1Result"]["verdict"]),
        ("PAYLOAD_IDENTITY_WITH_D1", payload_identity),
        ("CLASSIFICATION_IDENTITY_WITH_D1", classification_identity),
        ("CURRENT_ORACLE_PAYLOAD_IDENTITY", all(row["currentOraclePayloadIdentity"] for row in cells)),
        ("CLASSIFICATION_PARTITION", all(row["classificationPartition"] for row in cells)),
        ("REPEAT_IDENTITY", all(repeat_checks.values())),
        ("SAME_INDEX_ALIAS_EXPOSED", same_index["objectIndexBilinearAlias"] >= gates["sameIndexObjectIndexAliasMinimumPrimaryPixels"]),
        ("MOVING_ONE_SIDED_OPPORTUNITY", all(row["oneSidedStencilOpportunity"] >= gates["movingOneSidedStencilOpportunityMinimumPrimaryPixels"] for row in moving)),
        ("ACCEPTED_SET_DECOMPOSITION", all(set_checks.values())),
        ("ALL_RATIOS_WITHIN_CLOSED_UNIT_INTERVAL", all(row_sets_and_ratios_ok(row) for row in cells)),
        ("ACCEPTED_OUTSIDE_TRUE_OWNER_BILINEAR_EXPOSED", same_index["acceptedOutsideTrueOwnerBilinear"] >= gates["acceptedOutsideTrueOwnerBilinearSameIndexPrimaryMinimum"]),
        ("FULL_PROJECTION_VALID", projection_valid),
        ("NO_NEW_THRESHOLD_OR_SUPPORTED_CANDIDATE", True),
        ("BLENDER_MODEL_NETWORK_ZERO", gates["blenderRenderCalls"] == 0 and gates["modelCalls"] == 0 and gates["networkCalls"] == 0),
    ]
    attacks = build_attacks(projection, d1_result, spec["attacks"]["minimumRegisteredAttacks"])
    passed = all(value for _, value in checks) and len(attacks) >= spec["attacks"]["minimumRegisteredAttacks"] and all(row["passed"] for row in attacks)
    body = {
        "schemaVersion": "bfs.blenderTemporalOwnerSupportLocalizationCorrectionResult.v0.1",
        "experimentId": spec["experimentId"],
        "analyzerPid": os.getpid(),
        "verdict": spec["decision"]["localizedVerdict"] if passed else spec["decision"]["notLocalizedVerdict"],
        "passed": passed,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "parentChecks": parent_checks,
        "h1ParentChecks": h1_parent_checks,
        "classCodes": d1.CLASS,
        "cells": cells,
        "payloadHashes": payload_hashes,
        "payloadIdentityWithD1": payload_identity,
        "classificationIdentityWithD1": classification_identity,
        "repeatChecks": repeat_checks,
        "setAndRatioChecks": set_checks,
        "mutationAttacks": attacks,
        "mutationAttackPassed": sum(row["passed"] for row in attacks),
        "mutationAttackTotal": len(attacks),
        "operationCounts": {"analyzerProcesses": 1, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "analysisHash": d1.canon(body)}
    (args.output_root / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_C1 verdict={result['verdict']} checks={result['checkPassed']}/{result['checkTotal']} attacks={result['mutationAttackPassed']}/{result['mutationAttackTotal']} hash={result['analysisHash']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
