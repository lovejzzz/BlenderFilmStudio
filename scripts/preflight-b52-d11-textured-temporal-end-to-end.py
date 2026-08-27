#!/usr/bin/env python3
"""Zero-formal-output frozen-tool admission for B52-D11."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"
PREREGISTRATION_COMMIT = "c1751fca992bb522958dbd703637a0690f9f5496"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git_blob(root: Path, commit: str, uri: str) -> bytes:
    completed = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"missing frozen git blob: {uri}")
    return completed.stdout


def observe(path: Path, expected_sha: str, expected_bytes: int | None = None) -> dict:
    actual_sha = sha(path) if path.is_file() else None
    actual_bytes = path.stat().st_size if path.is_file() else None
    return {"uri": str(path), "expectedSha256": expected_sha, "actualSha256": actual_sha, "expectedBytes": expected_bytes, "actualBytes": actual_bytes, "match": actual_sha == expected_sha and (expected_bytes is None or actual_bytes == expected_bytes)}


def environment(spec: dict, config: str, scripts: str) -> dict[str, str]:
    result = {key: os.environ[key] for key in spec["runtime"]["environmentAllowlist"] if key in os.environ}
    result["OCIO"] = str(Path(spec["runtime"]["ocio"]["uri"]).resolve())
    result["BLENDER_USER_CONFIG"] = config
    result["BLENDER_USER_SCRIPTS"] = scripts
    return result


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    root = Path.cwd().resolve()
    spec = json.loads(args.spec.read_text())
    formal_root = root / spec["formalOutputRoot"]
    if sha(args.spec) != SPEC_SHA256 or args.output.exists() or formal_root.exists():
        raise RuntimeError("B52-D11 preflight identity/output/formal-root mismatch")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    if head != args.freeze_commit:
        raise RuntimeError("freeze commit must equal current HEAD")

    tools = {}
    for uri in spec["formalToolPaths"]:
        path = root / uri
        current = path.read_bytes() if path.is_file() else b""
        frozen = git_blob(root, args.freeze_commit, uri)
        tools[uri] = {"uri": uri, "sha256": hashlib.sha256(current).hexdigest() if current else None, "bytes": len(current), "freezeCommit": args.freeze_commit, "gitBlobSha256": hashlib.sha256(frozen).hexdigest(), "match": bool(current) and current == frozen}
    all_tools = len(tools) == 11 and all(item["match"] for item in tools.values())

    parents = {name: observe(root / item["uri"], item["sha256"]) for name, item in spec["parents"].items()}
    runtimes = {
        "blender": observe(Path(spec["runtime"]["blender"]["executable"]), spec["runtime"]["blender"]["sha256"], spec["runtime"]["blender"]["bytes"]),
        "python": observe(Path(spec["runtime"]["python"]["executable"]), spec["runtime"]["python"]["sha256"], spec["runtime"]["python"]["bytes"]),
        "node": observe(Path(spec["runtime"]["node"]["executable"]), spec["runtime"]["node"]["sha256"], spec["runtime"]["node"]["bytes"]),
        "ocio": observe(root / spec["runtime"]["ocio"]["uri"], spec["runtime"]["ocio"]["sha256"]),
    }
    parents_match = all(item["match"] for item in parents.values())
    runtime_match = all(item["match"] for item in runtimes.values())

    d9 = json.loads((root / spec["parents"]["d9_1Spec"]["uri"]).read_text())
    d10 = json.loads((root / spec["parents"]["d10_1Spec"]["uri"]).read_text())
    d9_resolutions = {tuple(item["resolution"]) for item in d9["fixtures"]}
    d10_names = {item["name"] for item in d10["scene"]["objects"]}
    d10_ids = {int(item["passIndex"]) for item in d10["scene"]["objects"]}
    d11_names = {item["name"] for fixture in spec["fixtures"] for item in fixture["objects"]}
    d11_ids = {int(item["passIndex"]) for fixture in spec["fixtures"] for item in fixture["objects"]}
    freshness = tuple(spec["scene"]["resolution"]) not in d9_resolutions and spec["scene"]["resolution"] != d10["sourceRender"]["resolution"] and spec["scene"]["camera"]["orthoScale"] != d10["scene"]["camera"]["orthoScale"] and d11_names.isdisjoint(d10_names) and d11_ids.isdisjoint(d10_ids)

    tests_argv = [spec["runtime"]["python"]["executable"], "-m", "unittest", "tests/test_b52_d11_textured_temporal_end_to_end_contract.py", "-v"]
    tests = subprocess.run(tests_argv, cwd=root, text=True, capture_output=True, check=False)
    test_ok = tests.returncode == 0 and "Ran 8 tests" in tests.stderr and "OK" in tests.stderr

    analyzer_source = (root / "scripts/analyze-b52-d11-textured-temporal-end-to-end.py").read_text()
    forbidden_imports_absent = all(token not in analyzer_source for token in ("import bpy", "import bpy_extras", "import mathutils", "from bpy", "from bpy_extras", "from mathutils"))
    with tempfile.TemporaryDirectory(prefix="bfs-d11-preflight-") as temporary, tempfile.TemporaryDirectory(prefix="bfs-d11-config-") as config, tempfile.TemporaryDirectory(prefix="bfs-d11-scripts-") as scripts:
        report = Path(temporary) / "blender-api.json"
        probe_code = (
            "import bpy,json,os; from pathlib import Path; "
            "bpy.ops.wm.read_factory_settings(use_empty=True); s=bpy.context.scene; l=bpy.context.view_layer; "
            "t=bpy.data.node_groups.new('BFS_D11_PREFLIGHT_TREE','CompositorNodeTree'); s.compositing_node_group=t; "
            "n=t.nodes.new('CompositorNodeImage'); n.name='BFS_D11_EXTERNAL_SOURCE'; t.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor'); "
            "g=t.nodes.new('NodeGroupOutput'); g.name='BFS_D11_GROUP_OUTPUT'; t.links.new(n.outputs['Image'],g.inputs['Image']); "
            f"Path({str(report)!r}).write_text(json.dumps({{'pid':os.getpid(),'passes':{{'combined':hasattr(l,'use_pass_combined'),'depth':hasattr(l,'use_pass_z'),'vector':hasattr(l,'use_pass_vector'),'objectIndex':hasattr(l,'use_pass_object_index')}},'graph':[f'{{x.from_node.name}}.{{x.from_socket.identifier}}->{{x.to_node.name}}.{{x.to_socket.identifier}}' for x in t.links],'renderCalls':0}}))"
        )
        probe_argv = [spec["runtime"]["blender"]["executable"], *spec["runtime"]["blender"]["launchFlags"], "--python-expr", probe_code]
        probe = subprocess.run(probe_argv, cwd=root, env=environment(spec, config, scripts), text=True, capture_output=True, check=False)
        probe_payload = json.loads(report.read_text()) if report.is_file() else {}
    probe_ok = probe.returncode == 0 and all(probe_payload.get("passes", {}).values()) and probe_payload.get("graph") == spec["rawExrBridge"]["blenderGraph"] and probe_payload.get("renderCalls") == 0

    available = shutil.disk_usage(root).free
    projected_after = available - spec["projectedWriteBytes"]
    disk = {"status": "ACCEPTED" if projected_after >= spec["diskReserveBytes"] else "REJECTED", "availableBytes": available, "projectedWriteBytes": spec["projectedWriteBytes"], "projectedAvailableAfterBytes": projected_after, "reserveBytes": spec["diskReserveBytes"]}
    formal_absent_after = not formal_root.exists()
    accepted = all([head == args.freeze_commit, all_tools, parents_match, runtime_match, freshness, test_ok, forbidden_imports_absent, probe_ok, formal_absent_after, disk["status"] == "ACCEPTED"])
    body = {
        "schemaVersion": "bfs.blenderRealTexturedTemporalFrozenToolPreflight.v0.1",
        "experimentId": spec["experimentId"],
        "classification": "ZERO_FORMAL_OUTPUT_FROZEN_TOOL_PREFLIGHT",
        "status": "ACCEPTED" if accepted else "REJECTED",
        "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(args.spec), "specSha256": SPEC_SHA256},
        "freezeCommit": args.freeze_commit,
        "spec": {"uri": str(args.spec), "sha256": sha(args.spec)},
        "tools": tools,
        "allFrozenToolsMatchGit": all_tools,
        "parents": parents,
        "parentsMatch": parents_match,
        "runtimes": runtimes,
        "runtimeMatch": runtime_match,
        "freshnessMatched": freshness,
        "analyzerForbiddenImportsAbsent": forbidden_imports_absent,
        "contractTests": {"argv": tests_argv, "exitCode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr, "passed": test_ok},
        "blenderApiProbe": {"argv": probe_argv, "exitCode": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr, "report": probe_payload, "passed": probe_ok},
        "diskAdmission": disk,
        "formalRoot": str(formal_root),
        "formalRootAbsent": not formal_root.exists() and formal_absent_after,
        "formalOperationCounts": {"childProcesses": 0, "blenderProcesses": 0, "renderCalls": 0, "cyclesRayRenders": 0, "formalMeasurements": 0},
        "nonClaims": ["Preflight creates no D11 formal output.", "The Blender API probe performs zero renders.", "Development smoke artifacts cannot satisfy formal gates."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({**body, "preflightHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_PREFLIGHT_{body['status']} tools={len(tools)} tests={test_ok} probe={probe_ok} outputAbsent={body['formalRootAbsent']}")
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
