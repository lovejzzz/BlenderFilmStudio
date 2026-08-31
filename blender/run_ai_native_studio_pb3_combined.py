#!/usr/bin/env python3
"""Trusted Blender-side PB.3 combined compile/workspace probe.

The proposal remains typed data. This script is fixed research tooling and is
only launched by the separately authorized PB.3 runner.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("build", "reopen"), required=True)
    parser.add_argument("--fixture-id", choices=("B01", "B02"), required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--tool-contract", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def write_exclusive(path: Path, value: object) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def fixture(contract: dict, fixture_id: str) -> dict:
    matches = [row for row in contract["fixtures"] if row["id"] == fixture_id]
    require(len(matches) == 1, "fixture contract is not unique")
    return matches[0]


def state_snapshot() -> dict:
    scene = bpy.context.scene
    state = scene.film_studio
    return {
        "schemaVersion": state.schema_version,
        "project": {"identifier": state.project.identifier, "name": state.project.name},
        "scene": {"identifier": state.story_scene.identifier, "name": state.story_scene.name},
        "character": {"identifier": state.character.identifier, "name": state.character.name},
        "shots": [
            {
                "identifier": shot.identifier,
                "name": shot.name,
                "camera": shot.camera.name if shot.camera else None,
            }
            for shot in state.shots
        ],
        "activeShotIndex": state.active_shot_index,
        "expertMode": state.expert_mode,
        "sceneCamera": scene.camera.name if scene.camera else None,
        "contractStatus": state.contract_status,
        "contractProposalId": state.contract_proposal_id,
        "contractApprovalScope": state.contract_approval_scope,
        "contractOutputUri": state.contract_output_uri,
        "contractPlanHash": state.contract_plan_hash,
        "planHash": scene.get("bfs_plan_hash"),
        "sceneSpecHash": scene.get("bfs_scene_spec_hash"),
        "structureHash": scene.get("bfs_structure_hash"),
        "structureIdentityVersion": scene.get("bfs_structure_identity_version"),
        "productBuildHash": scene.get("bfs_product_build_hash"),
    }


def without_expert(snapshot: dict) -> dict:
    return {key: value for key, value in snapshot.items() if key != "expertMode"}


def validate_snapshot(snapshot: dict, row: dict) -> None:
    mapping = row["workspaceMapping"]
    expected = {
        "schemaVersion": "bfs.filmWorkspace.v0.1",
        "project": mapping["project"],
        "scene": mapping["scene"],
        "character": mapping["character"],
        "shots": [{**mapping["shot"], "camera": mapping["cameraObject"]}],
        "activeShotIndex": 0,
        "expertMode": False,
        "sceneCamera": mapping["cameraObject"],
        "contractStatus": "COMPILED",
        "contractProposalId": row["proposalId"],
        "contractApprovalScope": "COMPILE_BUILD_PLAN / WRITE_BUILD_PLAN only",
        "contractOutputUri": row["outputUri"],
        "contractPlanHash": row["planHash"],
        "planHash": row["planHash"],
        "sceneSpecHash": row["sceneCanonicalSha256"],
        "structureHash": row["semanticStructureSha256"],
        "structureIdentityVersion": "bfs.semanticSceneStructure.v0.2",
        "productBuildHash": row["productBuildHash"],
    }
    require(snapshot == expected, "typed workspace or scene identity mismatch")


def set_workspace(row: dict) -> None:
    state = bpy.context.scene.film_studio
    mapping = row["workspaceMapping"]
    state.project.identifier = mapping["project"]["identifier"]
    state.project.name = mapping["project"]["name"]
    state.story_scene.identifier = mapping["scene"]["identifier"]
    state.story_scene.name = mapping["scene"]["name"]
    state.character.identifier = mapping["character"]["identifier"]
    state.character.name = mapping["character"]["name"]
    state.shots.clear()
    shot = state.shots.add()
    shot.identifier = mapping["shot"]["identifier"]
    shot.name = mapping["shot"]["name"]
    require(bpy.context.scene.camera is not None, "compiled scene camera is missing")
    require(bpy.context.scene.camera.name == mapping["cameraObject"], "compiled camera name mismatch")
    shot.camera = bpy.context.scene.camera
    state.active_shot_index = 0
    state.expert_mode = False


def toggle_roundtrip(row: dict) -> dict:
    state = bpy.context.scene.film_studio
    before = state_snapshot()
    validate_snapshot(before, row)
    state.expert_mode = True
    expert = state_snapshot()
    require(expert["expertMode"] is True, "Expert Mode did not activate")
    require(without_expert(expert) == without_expert(before), "Expert Mode changed film or scene state")
    state.expert_mode = False
    after = state_snapshot()
    require(after == before, "Film Mode roundtrip changed state")
    return {"before": before, "expert": expert, "after": after, "lossless": True}


def import_compile_scene(repository_root: Path):
    path = repository_root / "blender/compile_scene.py"
    spec = importlib.util.spec_from_file_location("pb3_frozen_compile_scene", path)
    require(spec is not None and spec.loader is not None, "cannot load frozen compile_scene tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(args: argparse.Namespace, contract: dict, row: dict) -> dict:
    root = args.fixture_root.resolve(strict=True)
    state = bpy.context.scene.film_studio
    state.contract_repository_root = str(root)
    state.contract_proposal_uri = row["proposalUri"]
    state.contract_approval_uri = row["approvalUri"]
    inspect_result = sorted(bpy.ops.film_studio.inspect_contract())
    require(inspect_result == ["FINISHED"], "contract inspection failed")
    require(state.contract_status == "APPROVED_READY", "contract did not become approved-ready")
    inspected = state_snapshot()
    execute_result = sorted(bpy.ops.film_studio.execute_contract())
    require(execute_result == ["FINISHED"], "approved compile failed")
    plan_path = root / row["outputUri"]
    require(plan_path.is_file() and sha256_file(plan_path) == row["buildPlanFileSha256"], "BuildPlan bytes mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    require(plan.get("planHash") == row["planHash"], "BuildPlan hash mismatch")

    artifact_root = root / row["artifactRoot"]
    compiler = import_compile_scene(args.repository_root.resolve(strict=True))
    saved_argv = sys.argv
    try:
        sys.argv = [
            str(args.repository_root / "blender/compile_scene.py"),
            "--", "--plan", str(plan_path), "--repository-root", str(root),
            "--output-dir", str(artifact_root),
        ]
        compiler.main()
    finally:
        sys.argv = saved_argv

    set_workspace(row)
    roundtrip = toggle_roundtrip(row)
    blend_path = artifact_root / "scene.blend"
    save_result = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False, compress=True))
    require(save_result == ["FINISHED"], "combined workspace save failed")
    final = state_snapshot()
    validate_snapshot(final, row)
    structure_path = artifact_root / "scene.structure.canonical.json"
    manifest_path = artifact_root / "scene.manifest.json"
    require(sha256_file(structure_path) == row["semanticStructureSha256"], "semantic structure mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["structureHash"] == row["semanticStructureSha256"], "manifest structure mismatch")
    return {
        "stage": "build",
        "inspection": inspected,
        "operations": {"inspect": inspect_result, "execute": execute_result, "save": save_result},
        "roundtrip": roundtrip,
        "final": final,
        "artifacts": {
            "buildPlan": {"sha256": sha256_file(plan_path), "bytes": plan_path.stat().st_size},
            "sceneBlend": {"sha256": sha256_file(blend_path), "bytes": blend_path.stat().st_size},
            "manifest": {"sha256": sha256_file(manifest_path), "bytes": manifest_path.stat().st_size},
            "structure": {"sha256": sha256_file(structure_path), "bytes": structure_path.stat().st_size},
        },
    }


def reopen(args: argparse.Namespace, row: dict) -> dict:
    before = state_snapshot()
    validate_snapshot(before, row)
    roundtrip = toggle_roundtrip(row)
    after = state_snapshot()
    validate_snapshot(after, row)
    return {"stage": "reopen", "before": before, "roundtrip": roundtrip, "after": after}


def main() -> None:
    args = parse_args()
    contract = json.loads(args.tool_contract.read_text(encoding="utf-8"))
    require(contract.get("schemaVersion") == "bfs.aiNativeStudioPb3ValidationToolFreeze.v0.2", "tool contract schema mismatch")
    row = fixture(contract, args.fixture_id)
    require(args.receipt.is_absolute() and not args.receipt.exists(), "receipt must be a fresh absolute path")
    body = build(args, contract, row) if args.stage == "build" else reopen(args, row)
    receipt = {
        "schemaVersion": "bfs.aiNativeStudioPb3CombinedProbeReceipt.v0.1",
        "status": "PASS",
        "fixtureId": args.fixture_id,
        **body,
        "counts": {"blenderStarts": 1, "renders": 0, "networkCalls": 0},
    }
    receipt["receiptHash"] = sha256_bytes(canonical(receipt))
    write_exclusive(args.receipt, receipt)
    print(f"PB3_COMBINED_{args.fixture_id}_{args.stage.upper()} PASS {receipt['receiptHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"PB3_COMBINED_FAIL {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
