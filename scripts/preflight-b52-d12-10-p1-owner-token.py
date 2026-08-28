#!/usr/bin/env python3
"""Zero-render admission preflight for B52-D12.10-P1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


SPEC_SHA256 = "7eb76c00baad8cbc4f996ec7a139e6a3cb1fd90c1c02391a531d8c2637abd4be"


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    root = args.output_root.resolve()
    formal_root = (repo / spec["freshness"]["formalRoot"]).resolve()
    if sha_file(args.spec) != SPEC_SHA256 or root != (repo / spec["freshness"]["preflightRoot"]).resolve() or root.exists() or formal_root.exists():
        raise RuntimeError("D12.10-P1 preflight freshness mismatch")
    parent_checks = {name: sha_file(repo / row["uri"]) == row["sha256"] for name, row in spec["parents"].items()}
    runtime_checks = {
        "blender": sha_file(Path(spec["runtime"]["blender"]["executable"])) == spec["runtime"]["blender"]["sha256"],
        "python": sha_file(Path(spec["runtime"]["python"]["executable"])) == spec["runtime"]["python"]["sha256"],
        "ocio": sha_file(repo / spec["runtime"]["ocio"]["uri"]) == spec["runtime"]["ocio"]["sha256"],
    }
    tool_paths = spec["freshness"]["newToolPaths"]
    if not all((repo / path).is_file() for path in tool_paths):
        raise RuntimeError("D12.10-P1 preflight tool missing")
    tool_hashes = {path: sha_file(repo / path) for path in tool_paths}
    freeze_commit = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    frozen_blob_checks = {}
    for path, digest in tool_hashes.items():
        process = git(repo, "show", f"{freeze_commit}:{path}", check=False)
        frozen_blob_checks[path] = process.returncode == 0 and sha_bytes(process.stdout) == digest
    preregistration_commit = git(repo, "log", "-1", "--format=%H", "--", str(args.spec.resolve().relative_to(repo))).stdout.decode().strip()
    prereg_absence = {path: git(repo, "cat-file", "-e", f"{preregistration_commit}:{path}", check=False).returncode != 0 for path in tool_paths}
    available = shutil.disk_usage(repo).free
    projected = spec["diskAdmission"]["projectedWriteBytes"]
    reserve = spec["diskAdmission"]["minimumReserveBytes"]
    disk_ok = available - projected >= reserve
    if not all(parent_checks.values()) or not all(runtime_checks.values()) or not all(frozen_blob_checks.values()) or not all(prereg_absence.values()) or not disk_ok:
        raise RuntimeError("D12.10-P1 preflight admission rejected")

    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    probe_rows = []
    source = repo / "blender/render_b52_d12_10_p1_owner_token_source.py"
    for display in spec["sceneContract"]["displayCells"]:
        display_id = display["id"]
        probe_dir = root / "probes" / display_id
        runtime_dir = root / "runtime" / display_id
        report = probe_dir / "report.json"
        stdout_path, stderr_path = probe_dir / "stdout.log", probe_dir / "stderr.log"
        env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OCIO": str((repo / spec["runtime"]["ocio"]["uri"]).resolve())}
        for name, suffix in (("TMPDIR", "tmp"), ("BLENDER_USER_CONFIG", "config"), ("BLENDER_USER_SCRIPTS", "scripts")):
            target = runtime_dir / suffix
            target.mkdir(parents=True, exist_ok=True)
            env[name] = str(target)
        command = [spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python", str(source), "--", "--spec", str(args.spec.resolve()), "--frame", "0", "--display-cell", display_id, "--repeat", "1", "--report", str(report), "--probe-only"]
        tick = time.monotonic()
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        probe_dir.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        if process.returncode != 0:
            raise RuntimeError(f"D12.10-P1 probe failed: {display_id}")
        data = json.loads(report.read_text())
        checks = {
            "selfHash": data["reportHash"] == canon({key: value for key, value in data.items() if key != "reportHash"}),
            "zeroRender": data["probeOnly"] is True and data["output"] is None and data["operationCounts"]["blenderRenderCalls"] == 0,
            "displayRoundTrip": data["display"] == {key: display[key] for key in ("displayDevice", "viewTransform", "look", "exposure", "gamma")},
            "materialPass": data["passState"]["Material Index"] is True and data["passState"]["materialPassIndexRange"] == [0, 32767],
            "aovApi": data["passState"]["registeredAov"] == {"name": "OwnerToken", "type": "VALUE", "isValid": True} and data["passState"]["viewLayerAovFunctions"] == ["add", "remove"] and data["passState"]["outputAovNodeAvailable"] is True,
            "ownerRoundTrip": [(row["objectIndex"], row["materialIndex"], row["customAovValue"]) for row in data["scene"]["owners"]] == [(7, 11, 0.25), (7, 23, 0.75)],
        }
        probe_rows.append({"displayCell": display_id, "pid": data["pid"], "exitCode": process.returncode, "elapsedSeconds": round(time.monotonic() - tick, 6), "checks": checks, "passed": all(checks.values()), "report": {"uri": str(report), "sha256": sha_file(report)}, "stdout": {"uri": str(stdout_path), "sha256": sha_file(stdout_path)}, "stderr": {"uri": str(stderr_path), "sha256": sha_file(stderr_path)}})
    checks = [
        ("SPEC_PARENT_IDENTITY", all(parent_checks.values())),
        ("RUNTIME_IDENTITY", all(runtime_checks.values())),
        ("PREREGISTRATION_TOOL_ABSENCE", all(prereg_absence.values())),
        ("TOOL_BLOB_FREEZE", all(frozen_blob_checks.values())),
        ("TWO_UNIQUE_ZERO_RENDER_PROCESSES", len({row["pid"] for row in probe_rows}) == 2 and all(row["passed"] for row in probe_rows)),
        ("DISPLAY_CELLS_ROUND_TRIP", all(row["checks"]["displayRoundTrip"] for row in probe_rows)),
        ("MATERIAL_INDEX_API", all(row["checks"]["materialPass"] for row in probe_rows)),
        ("CUSTOM_AOV_API", all(row["checks"]["aovApi"] for row in probe_rows)),
        ("OWNER_ASSIGNMENTS_ROUND_TRIP", all(row["checks"]["ownerRoundTrip"] for row in probe_rows)),
        ("FORMAL_ROOT_ABSENT", not formal_root.exists()),
        ("DISK_ADMISSION", disk_ok),
        ("MODEL_NETWORK_ZERO", all(json.loads(Path(row["report"]["uri"]).read_text())["operationCounts"]["modelCalls"] == 0 and json.loads(Path(row["report"]["uri"]).read_text())["operationCounts"]["networkCalls"] == 0 for row in probe_rows)),
    ]
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbePreflight.v0.1",
        "experimentId": spec["experimentId"],
        "status": "ACCEPTED" if all(value for _, value in checks) else "REJECTED",
        "preflightPid": os.getpid(),
        "preregistrationCommit": preregistration_commit,
        "toolFreezeCommit": freeze_commit,
        "toolHashes": tool_hashes,
        "parentChecks": parent_checks,
        "runtimeChecks": runtime_checks,
        "preregistrationAbsenceChecks": prereg_absence,
        "frozenBlobChecks": frozen_blob_checks,
        "checks": [{"id": name, "passed": bool(value)} for name, value in checks],
        "checkPassed": sum(value for _, value in checks),
        "checkTotal": len(checks),
        "probeRows": probe_rows,
        "diskAdmission": {"availableBytes": available, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": available - projected, "passed": disk_ok},
        "operationCounts": {"preflightProcesses": 1, "blenderProbeProcesses": 2, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "elapsedSeconds": round(time.monotonic() - started, 6),
    }
    result = {**body, "preflightHash": canon(body)}
    (root / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_PREFLIGHT status={result['status']} checks={result['checkPassed']}/{result['checkTotal']} hash={result['preflightHash']}")
    raise SystemExit(0 if result["status"] == "ACCEPTED" else 1)


if __name__ == "__main__":
    main()
