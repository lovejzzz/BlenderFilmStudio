#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Development-only PC9 physics and four-still visual probe."""

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

import bpy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-root", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--scene-spec-uri", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(root):
    sys.modules.pop("film_studio_causal", None)
    sys.path.insert(0, str(root))
    return importlib.import_module("film_studio_causal")


def render(scene, camera, frame, path, motion_blur, shutter, position):
    for current in range(scene.frame_start, frame + 1):
        scene.frame_set(current)
        bpy.context.view_layer.update()
    scene.camera = camera
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = shutter
    scene.render.motion_blur_position = position
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "uri": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}


args = parse_args()
args.output_root.mkdir(parents=True, exist_ok=False)
module = load_module(args.module_root.resolve(strict=True))
inspection = module.inspect_causal_scene(str(args.repository_root.resolve(strict=True)), args.scene_spec_uri)
result = module.execute_causal_scene(str(args.repository_root.resolve(strict=True)), args.scene_spec_uri, inspection["inspectionToken"])
scene = bpy.context.scene
blur = result["cinematography"]["motionBlur"]
impact = result["physics"]["motionSelection"]["impactFrame"]
frames = {shot: result["framing"][shot]["frame"] for shot in ("SETUP", "IMPACT", "AFTERMATH")}
renders = []
renders.append({"shotId": "SETUP", **render(scene, bpy.data.objects["CAUSAL_CAM_SETUP"], frames["SETUP"], args.output_root / "setup.png", True, blur["computedShutterFrames"], blur["position"])})
renders.append({"shotId": "IMPACT_SHARP", **render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], impact, args.output_root / "impact-sharp.png", False, blur["computedShutterFrames"], blur["position"])})
renders.append({"shotId": "IMPACT_MEASURED", **render(scene, bpy.data.objects["CAUSAL_CAM_IMPACT"], impact, args.output_root / "impact-measured.png", True, blur["computedShutterFrames"], blur["position"])})
renders.append({"shotId": "AFTERMATH", **render(scene, bpy.data.objects["CAUSAL_CAM_AFTERMATH"], frames["AFTERMATH"], args.output_root / "aftermath.png", True, blur["computedShutterFrames"], blur["position"])})
blend = args.output_root / "pc9-development.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
probe = {
    "schemaVersion": "bfs.pc9PhysicalArchetypesDevelopmentProbe.v0.1",
    "status": "DEVELOPMENT_ONLY_NOT_FORMAL",
    "module": {"path": str(Path(module.__file__).resolve()), "sha256": sha256_file(Path(module.__file__))},
    "inspection": inspection,
    "physics": result["physics"],
    "physicalArchetypes": result["physicalArchetypes"],
    "initialConditions": result["initialConditions"],
    "cinematography": result["cinematography"],
    "framing": result["framing"],
    "provenance": result["provenance"],
    "semanticRoster": result["semanticRoster"],
    "renders": renders,
    "blend": {"path": str(blend), "sha256": sha256_file(blend), "bytes": blend.stat().st_size},
    "networkCalls": 0,
}
(args.output_root / "probe.json").write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("PC9_DEVELOPMENT=" + json.dumps(probe, sort_keys=True, separators=(",", ":")))
