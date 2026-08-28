#!/usr/bin/env python3
"""Render one fresh D12.14-P1 Position-oracle development source."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import bpy


SPEC_SHA256 = "2ccffbcfe861fd80406901b417cf4cd2b2b8977c6925d6fb73e3d0328092efe3"
H1_SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"
H1_SOURCE_SHA256 = "9ba86e95e8d24c2592690c575cd87749433a1af00a7d2c18ace3e2153daf36ce"
FIXTURE_ID = "RIGID_NEITHER_FRESH_197X139"
FRAME = 1


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output-exr", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def load_h1(root: Path):
    path = root / "blender/render_b52_d12_14_h1_rigid_directional_source.py"
    if sha_file(path) != H1_SOURCE_SHA256:
        raise RuntimeError("P1 frozen H1 source identity mismatch")
    module_spec = importlib.util.spec_from_file_location("bfs_d1214_h1_source", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("P1 cannot load frozen H1 source")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def main() -> None:
    cli = arguments()
    root = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output_exr.exists() or cli.report.exists():
        raise RuntimeError("P1 spec identity or fresh output violation")
    spec = json.loads(cli.spec.read_text())
    if spec.get("experimentId") != "B52-D12.14-P1":
        raise RuntimeError("P1 experiment identity mismatch")

    h1_spec_path = root / spec["parents"]["h1Spec"]["uri"]
    if sha_file(h1_spec_path) != H1_SPEC_SHA256:
        raise RuntimeError("P1 H1 spec identity mismatch")
    h1_spec = json.loads(h1_spec_path.read_text())
    h1 = load_h1(root)

    runtime = spec["runtime"]
    if sha_file(Path(bpy.app.binary_path)) != runtime["blender"]["sha256"]:
        raise RuntimeError("P1 Blender executable identity mismatch")
    if bpy.app.version_string != runtime["blender"]["version"] or bpy.app.build_hash.decode() != runtime["blender"]["buildHash"]:
        raise RuntimeError("P1 Blender version identity mismatch")
    if sha_file(Path(os.environ["OCIO"])) != runtime["ocio"]["sha256"]:
        raise RuntimeError("P1 OCIO identity mismatch")

    fixture = next(row for row in h1_spec["fixtures"] if row["id"] == FIXTURE_ID)
    fixture = h1.effective_fixture(h1_spec, fixture)
    started = time.monotonic()
    scene, camera, owners = h1.setup(h1_spec, fixture, FRAME, cli.repeat)
    scene.name = f"BFS_D1214P1_{FIXTURE_ID}_F{FRAME}_R{cli.repeat}"
    layer = bpy.context.view_layer
    layer.name = "BFS_D1214P1_MASTER"
    layer.use_pass_position = True
    bpy.context.view_layer.update()

    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentSource.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "fixtureId": FIXTURE_ID,
        "frame": FRAME,
        "repeat": cli.repeat,
        "pid": os.getpid(),
        "parent": {
            "h1SpecSha256": H1_SPEC_SHA256,
            "h1SourceToolSha256": H1_SOURCE_SHA256,
        },
        "runtime": {
            "blender": bpy.app.version_string,
            "buildHash": bpy.app.build_hash.decode(),
            "executableSha256": sha_file(Path(bpy.app.binary_path)),
            "engine": scene.render.engine,
            "device": scene.cycles.device,
            "samples": scene.cycles.samples,
            "seed": scene.cycles.seed,
        },
        "sceneStructure": {
            "scene": scene.name,
            "camera": {
                "name": camera.name,
                "type": camera.data.type,
                "lensMm": float(camera.data.lens),
                "sensorWidthMm": float(camera.data.sensor_width),
                "location": [float(value) for value in camera.location],
                "rotationEuler": [float(value) for value in camera.rotation_euler],
            },
            "owners": [h1.owner_structure(owner, owner_spec) for owner, owner_spec in zip(owners, fixture["owners"])],
        },
        "animation": {
            "camera": h1.action_rows(camera),
            "owners": {owner.name: h1.action_rows(owner) for owner in owners},
        },
        "passState": {
            "viewLayer": layer.name,
            "Combined": layer.use_pass_combined,
            "Depth": layer.use_pass_z,
            "Position": layer.use_pass_position,
            "Vector": layer.use_pass_vector,
            "Object Index": layer.use_pass_object_index,
            "Material Index": layer.use_pass_material_index,
            "passAlphaThreshold": layer.pass_alpha_threshold,
        },
    }

    cli.output_exr.parent.mkdir(parents=True, exist_ok=True)
    render_started = time.monotonic()
    outcome = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in outcome:
        raise RuntimeError("P1 Blender render failed")
    render_seconds = time.monotonic() - render_started
    bpy.data.images["Render Result"].save_render(str(cli.output_exr), scene=scene)
    body["output"] = {
        "uri": str(cli.output_exr.relative_to(root)),
        "sha256": sha_file(cli.output_exr),
        "bytes": cli.output_exr.stat().st_size,
    }
    body["operationCounts"] = {
        "blenderProcesses": 1,
        "blenderRenderCalls": 1,
        "cyclesRayRenders": 1,
        "modelCalls": 0,
        "networkCalls": 0,
    }
    body["renderSeconds"] = round(render_seconds, 6)
    body["elapsedSeconds"] = round(time.monotonic() - started, 6)
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D1214P1_SOURCE_OK repeat={cli.repeat} exr={body['output']['sha256']}")


if __name__ == "__main__":
    main()
