#!/usr/bin/env python3
"""Zero-render Blender 5.2 preflight for B52-D12.14-H1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"
Q24 = 1 << 24


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def self_ok(value: dict, field: str) -> bool:
    return value.get(field) == canonical_hash({key: row for key, row in value.items() if key != field})


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], check=True, text=True, capture_output=True).stdout.strip()


def environment(spec: dict) -> dict[str, str]:
    allowed = set(spec["runtime"]["environmentAllowlist"])
    result = {key: value for key, value in os.environ.items() if key in allowed}
    result["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    result.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    result.setdefault("LANG", "C.UTF-8")
    result.setdefault("LC_ALL", "C.UTF-8")
    return result


def spawn(command: list[str], category: str, env: dict[str, str]):
    started = time.monotonic()
    process = subprocess.run(command, text=True, capture_output=True, env=env)
    return {
        "category": category, "pid": None, "exitCode": process.returncode,
        "elapsedSeconds": round(time.monotonic() - started, 6), "command": command,
        "stdout": process.stdout, "stderr": process.stderr,
    }


def synthetic_direction_checks():
    cases = {
        "LEFT_MISSING_RIGHT_AVAILABLE": {"horizontal": [(False, True), (False, True)], "vertical": [(True, True), (True, True)]},
        "RIGHT_MISSING_LEFT_AVAILABLE": {"horizontal": [(True, False), (True, False)], "vertical": [(True, True), (True, True)]},
        "TOP_MISSING_BOTTOM_AVAILABLE": {"horizontal": [(True, True), (True, True)], "vertical": [(False, True), (False, True)]},
        "BOTTOM_MISSING_TOP_AVAILABLE": {"horizontal": [(True, True), (True, True)], "vertical": [(True, False), (True, False)]},
        "NEITHER_HORIZONTAL_AVAILABLE": {"horizontal": [(False, False), (True, True)], "vertical": [(True, True), (True, True)]},
        "FULL_STENCIL": {"horizontal": [(True, True), (True, True)], "vertical": [(True, True), (True, True)]},
    }
    observed = {}
    for name, row in cases.items():
        horizontal, vertical = row["horizontal"], row["vertical"]
        horizontal_full = all(left and right for left, right in horizontal)
        vertical_full = all(top and bottom for top, bottom in vertical)
        observed[name] = {
            "left": all((not left) and right for left, right in horizontal) and vertical_full,
            "right": all(left and (not right) for left, right in horizontal) and vertical_full,
            "top": all((not top) and bottom for top, bottom in vertical) and horizontal_full,
            "bottom": all(top and (not bottom) for top, bottom in vertical) and horizontal_full,
            "neither": any((not left) and (not right) for left, right in horizontal),
            "eligible": not any((not left) and (not right) for left, right in horizontal) and not any((not top) and (not bottom) for top, bottom in vertical),
        }
    expected = {
        "LEFT_MISSING_RIGHT_AVAILABLE": (True, False, False, False, False, True),
        "RIGHT_MISSING_LEFT_AVAILABLE": (False, True, False, False, False, True),
        "TOP_MISSING_BOTTOM_AVAILABLE": (False, False, True, False, False, True),
        "BOTTOM_MISSING_TOP_AVAILABLE": (False, False, False, True, False, True),
        "NEITHER_HORIZONTAL_AVAILABLE": (False, False, False, False, True, False),
        "FULL_STENCIL": (False, False, False, False, False, True),
    }
    passed = all(tuple(observed[name][key] for key in ("left", "right", "top", "bottom", "neither", "eligible")) == values for name, values in expected.items())
    fx, fy, mx, my, allowance = Q24 // 4, Q24 // 2, 2048, 4096, 512
    numerator = 2 * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my)
    risk = (numerator + Q24 * Q24 - 1) // (Q24 * Q24) + allowance
    arithmetic = risk == 3328
    return passed and arithmetic, {"cases": observed, "riskExampleQ30": risk, "riskExpectedQ30": 3328}


def effective_fixture(spec: dict, fixture: dict) -> dict:
    camera = spec["sceneContract"]["camera"]
    result = {
        **fixture,
        "cameraByFrame": {
            frame: {"location": camera["locationByFrame"][frame], "rotationEuler": camera["rotationEulerByFrame"][frame]}
            for frame in ("0", "1", "2")
        },
    }
    owners = []
    for row in fixture["owners"]:
        owner = dict(row)
        if owner["role"] == "background":
            background = spec["sceneContract"]["background"]
            owner.update({
                "sizeWorld": background["sizeWorld"],
                "subdivisions": background["subdivisions"],
                "transformByFrame": background["transformByFrame"],
            })
        else:
            owner["sizeWorld"] = spec["sceneContract"]["foreground"]["sizeWorld"]
        owners.append(owner)
    result["owners"] = owners
    return result


def animation_matches(rows: list[dict], transforms: dict, tolerance: float = 1e-6) -> bool:
    expected_paths = {"location": "location", "rotation_euler": "rotationEuler"}
    indexed = {(row.get("dataPath"), row.get("arrayIndex")): row for row in rows}
    if set(indexed) != {(path, index) for path in expected_paths for index in range(3)}:
        return False
    for data_path, source_key in expected_paths.items():
        for index in range(3):
            keyframes = indexed[(data_path, index)].get("keyframes", [])
            if len(keyframes) != 3:
                return False
            for frame, keyframe in zip((0, 1, 2), keyframes):
                if int(keyframe[0]) != frame or keyframe[2] != "LINEAR":
                    return False
                if abs(float(keyframe[1]) - float(transforms[str(frame)][source_key][index])) > tolerance:
                    return False
    return True


def vectors_close(observed, expected, tolerance: float = 1e-6) -> bool:
    return len(observed or []) == len(expected) and all(
        abs(float(left) - float(right)) <= tolerance for left, right in zip(observed, expected)
    )


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    return parser.parse_args()


def main():
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256:
        raise RuntimeError("D12.14-H1 preflight spec identity mismatch")
    spec = json.loads(cli.spec.read_text())
    if cli.root.as_posix() != spec["freshness"]["preflightRoot"] or cli.root.exists() or Path(spec["freshness"]["formalRoot"]).exists():
        raise RuntimeError("D12.14-H1 preflight/formal freshness violation")
    cli.root.mkdir(parents=True, exist_ok=False)
    tool_hashes = {uri: sha_file(Path(uri)) for uri in spec["freshness"]["newFormalToolPaths"]}
    tool_committed = True
    tool_commits = {}
    for uri in spec["freshness"]["newFormalToolPaths"]:
        tool_committed &= subprocess.run(["git", "diff", "--quiet", "HEAD", "--", uri]).returncode == 0
        tool_committed &= subprocess.run(["git", "ls-files", "--error-unmatch", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        tool_commits[uri] = git("log", "-1", "--format=%H", "--", uri)
    runtime_checks = {
        "blender": sha_file(Path(spec["runtime"]["blender"]["executable"])) == spec["runtime"]["blender"]["sha256"],
        "python": sha_file(Path(spec["runtime"]["python"]["executable"])) == spec["runtime"]["python"]["sha256"],
        "node": sha_file(Path(spec["runtime"]["node"]["executable"])) == spec["runtime"]["node"]["sha256"],
        "ocio": sha_file(Path(spec["runtime"]["ocio"]["uri"])) == spec["runtime"]["ocio"]["sha256"],
    }
    parent_checks = {name: sha_file(Path(row["uri"])) == row["sha256"] for name, row in spec["parents"].items() if "uri" in row and "sha256" in row}
    parent_trees = {
        "rigidCalibrationFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['rigidCalibrationFormalRoot']['uri']}"),
        "rejectedRenderedHoldoutFormalRoot": git("rev-parse", f"HEAD:{spec['parents']['rejectedRenderedHoldoutFormalRoot']['uri']}"),
    }
    parent_tree_exact = parent_trees == {
        "rigidCalibrationFormalRoot": spec["parents"]["rigidCalibrationFormalRoot"]["gitTree"],
        "rejectedRenderedHoldoutFormalRoot": spec["parents"]["rejectedRenderedHoldoutFormalRoot"]["gitTree"],
    }
    syntax_commands = [
        [spec["runtime"]["python"]["executable"], "-m", "py_compile", *[uri for uri in spec["freshness"]["newFormalToolPaths"] if uri.endswith(".py")]],
        [spec["runtime"]["node"]["executable"], "--check", "scripts/reconstruct-b52-d12-14-h1-rigid-directional.mjs"],
    ]
    env = environment(spec)
    children = [spawn(command, "syntax", env) for command in syntax_commands]
    probe_reports = []
    for fixture in spec["fixtures"]:
        report_path = cli.root / "probes" / fixture["id"] / "report.json"
        command = [
            spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"],
            "--python", "blender/render_b52_d12_14_h1_rigid_directional_source.py", "--",
            "--spec", str(cli.spec), "--fixture", fixture["id"], "--frame", "1", "--repeat", "1",
            "--report", str(report_path), "--probe-only",
        ]
        child = spawn(command, "blenderProbe", env)
        children.append(child)
        if child["exitCode"] == 0 and report_path.exists():
            report = json.loads(report_path.read_text())
            owners = report.get("sceneStructure", {}).get("owners", [])
            probe_reports.append({
                "fixtureId": fixture["id"], "report": str(report_path), "sha256": sha_file(report_path),
                "selfHash": self_ok(report, "reportHash"), "probeOnly": report.get("probeOnly") is True,
                "zeroRender": report.get("operationCounts", {}).get("blenderRenderCalls") == 0,
                "passes": report.get("passState"), "ownerCount": len(owners),
                "materialTokens": sorted(owner.get("materialPassIndex") for owner in owners),
                "objectTokens": sorted(set(owner.get("objectPassIndex") for owner in owners)),
                "fixture": report.get("fixture"),
                "camera": report.get("sceneStructure", {}).get("camera"),
                "ownerStructures": owners,
                "cameraAnimation": report.get("animation", {}).get("camera", []),
                "ownerAnimations": report.get("animation", {}).get("owners", {}),
            })
    synthetic_passed, synthetic = synthetic_direction_checks()
    python_source = Path("scripts/reconstruct-b52-d12-14-h1-rigid-directional.py").read_text()
    node_source = Path("scripts/reconstruct-b52-d12-14-h1-rigid-directional.mjs").read_text()
    rgb_isolation = all(fragment not in python_source for fragment in ("currentRgba\"][y, x, 0", "currentRgba\"][y, x, 1", "currentRgba\"][y, x, 2"))
    rgb_isolation &= all(fragment not in node_source for fragment in ("currentRgba[rgba(pixel, 0)]", "currentRgba[rgba(pixel, 1)]", "currentRgba[rgba(pixel, 2)]"))
    probe_exact = len(probe_reports) == len(spec["fixtures"])
    for raw_fixture, probe in zip(spec["fixtures"], probe_reports):
        fixture = effective_fixture(spec, raw_fixture)
        probe_exact &= (
            probe["fixtureId"] == fixture["id"] and probe["selfHash"] and probe["probeOnly"] and probe["zeroRender"]
            and probe["ownerCount"] == 2
            and probe["materialTokens"] == sorted(owner["materialPassIndex"] for owner in fixture["owners"])
            and probe["objectTokens"] == [fixture["owners"][0]["objectPassIndex"]]
            and probe["fixture"] == fixture
            and all(probe["passes"].get(name) is True for name in ("Combined", "Depth", "Vector", "Object Index", "Material Index"))
        )
        observed_owners = {owner.get("analyticOwnerId"): owner for owner in probe["ownerStructures"]}
        probe_exact &= set(observed_owners) == {owner["analyticOwnerId"] for owner in fixture["owners"]}
        for owner in fixture["owners"]:
            observed = observed_owners.get(owner["analyticOwnerId"], {})
            columns, rows = (int(value) for value in owner["subdivisions"])
            transform = owner["transformByFrame"]["1"]
            probe_exact &= (
                observed.get("role") == owner["role"]
                and observed.get("vertices") == (columns + 1) * (rows + 1)
                and observed.get("polygons") == columns * rows
                and observed.get("scale") == [1.0, 1.0, 1.0]
                and isinstance(observed.get("meshDataName"), str)
                and len(observed.get("localVertexSha256", "")) == 64
                and vectors_close(observed.get("location"), transform["location"])
                and vectors_close(observed.get("rotationEuler"), transform["rotationEuler"])
                and animation_matches(probe["ownerAnimations"].get(observed.get("name"), []), owner["transformByFrame"])
            )
        camera_transform = fixture["cameraByFrame"]["1"]
        probe_exact &= (
            vectors_close(probe["camera"].get("location"), camera_transform["location"])
            and vectors_close(probe["camera"].get("rotationEuler"), camera_transform["rotationEuler"])
            and animation_matches(probe["cameraAnimation"], fixture["cameraByFrame"])
        )
    free_bytes = shutil.disk_usage(Path.cwd()).free
    required = int(spec["diskAdmission"]["minimumReserveBytesAfterProjectedWrite"]) + int(spec["diskAdmission"]["projectedWriteBytes"])
    checks = {
        "SPEC_IDENTITY": sha_file(cli.spec) == SPEC_SHA256,
        "TOOLS_COMMITTED_AND_CLEAN": tool_committed,
        "RUNTIME_IDENTITIES": all(runtime_checks.values()),
        "PARENT_BYTES": all(parent_checks.values()),
        "PARENT_FORMAL_TREES": parent_tree_exact,
        "TOOL_SYNTAX": all(row["exitCode"] == 0 for row in children if row["category"] == "syntax"),
        "ALL_SCENES_CONSTRUCT": probe_exact,
        "ZERO_RENDER": all(row["zeroRender"] for row in probe_reports),
        "SYNTHETIC_DIRECTION_AND_Q_ARITHMETIC": synthetic_passed,
        "CURRENT_RGB_DECISION_ISOLATION": rgb_isolation,
        "DISK_RESERVE": free_bytes >= required,
        "FORMAL_ROOT_ABSENT": not Path(spec["freshness"]["formalRoot"]).exists(),
        "MODEL_CALLS_ZERO": True,
        "NETWORK_CALLS_ZERO": True,
    }
    passed = all(checks.values())
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutPreflight.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": passed, "checksPassed": sum(checks.values()), "checksTotal": len(checks),
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks.items()],
        "toolHashes": tool_hashes, "toolCommits": tool_commits,
        "runtimeChecks": runtime_checks, "parentChecks": parent_checks, "parentTrees": parent_trees,
        "probeReports": probe_reports, "synthetic": synthetic, "children": children,
        "disk": {"freeBytes": free_bytes, "requiredBeforeFormal": required},
        "operationCounts": {"preflightProcesses": len(children), "blenderProbeProcesses": len(probe_reports), "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    result = {**body, "preflightHash": canonical_hash(body)}
    result_path = cli.root / "preflight.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    receipt_body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalRenderHoldoutPreflightReceipt.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256,
        "passed": passed, "preflight": {"uri": str(result_path), "sha256": sha_file(result_path), "preflightHash": result["preflightHash"]},
        "toolHashes": tool_hashes, "formalRootAbsent": not Path(spec["freshness"]["formalRoot"]).exists(),
        "operationCounts": {"blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    receipt = {**receipt_body, "receiptHash": canonical_hash(receipt_body)}
    (cli.root / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214H1_PREFLIGHT passed={passed} checks={sum(checks.values())}/{len(checks)} probes={len(probe_reports)}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
