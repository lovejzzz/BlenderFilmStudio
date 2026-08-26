"""Reopen a compiled .blend and report its embedded BFS execution bindings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def text(value) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def main() -> None:
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    scene = bpy.context.scene
    report = {
        "documentType": "BFS_COMPILED_BLEND_AUDIT",
        "version": "0.1.0",
        "blender": {"version": bpy.app.version_string, "buildHash": text(bpy.app.build_hash)},
        "scene": {
            "name": scene.name,
            "frameStart": scene.frame_start,
            "frameEnd": scene.frame_end,
            "planHash": scene.get("bfs_plan_hash"),
            "sourceSceneCanonicalSha256": scene.get("bfs_scene_spec_hash"),
            "structureHash": scene.get("bfs_structure_hash"),
            "manifestVersion": scene.get("bfs_manifest_version"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_COMPILED_BLEND_AUDIT_OK {report['scene']['planHash']} {report['scene']['structureHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_COMPILED_BLEND_AUDIT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
