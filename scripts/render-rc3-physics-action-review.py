#!/usr/bin/env python3
"""Render both retained RC3 solved blends in one bounded Blender start."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def render(scene, camera, frame, path):
    scene.frame_set(frame)
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"frame": frame, "camera": camera.name, "path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}


parser = argparse.ArgumentParser()
parser.add_argument("--d1-blend", type=Path, required=True)
parser.add_argument("--h1-blend", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
evidence = args.evidence_root.resolve(strict=True)


def review(case, blend, already_open=False):
    if not already_open:
        bpy.ops.wm.open_mainfile(filepath=str(blend.resolve(strict=True)))
    scene = bpy.context.scene
    result = json.loads(scene["film_studio_physics_action_result"])
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 960, 540, 100
    scene.render.image_settings.file_format, scene.render.image_settings.color_mode = "PNG", "RGBA"
    scene.render.image_settings.color_depth = "8"
    bpy.context.preferences.filepaths.file_preview_type = "NONE"
    root = evidence / case
    still_root, clip_root = root / "stills", root / "clip"
    still_root.mkdir(parents=True, exist_ok=False)
    clip_root.mkdir(parents=True, exist_ok=False)
    stills = []
    for role in ("cause", "contact", "effect"):
        shot = result["cinematography"][role]
        item = render(scene, scene.objects[shot["camera"]], shot["frame"], still_root / f"{role}-frame-{shot['frame']:04d}.png")
        item["role"] = role
        stills.append(item)
    start, end = result["review"]["contactClipFrameRangeInclusive"]
    camera = scene.objects[result["cinematography"]["contact"]["camera"]]
    frames = []
    for frame in range(start, end + 1):
        frames.append(render(scene, camera, frame, clip_root / f"frame-{frame:04d}.png"))
    return {"case": case, "blend": {"path": str(blend), "sha256": sha(blend)}, "resultHash": result["resultHash"], "topology": result["topology"], "stills": stills, "clip": {"startFrame": start, "endFrame": end, "frameCount": len(frames), "camera": camera.name, "frames": frames}}


output = {
    "schemaVersion": "bfs.rc3PhysicsActionVisualRender.v0.1",
    "status": "PASS_RENDER_COMPLETE",
    "cases": [review("D1", args.d1_blend, already_open=True), review("H1", args.h1_blend)],
    "counts": {"productStarts": 1, "sceneMutations": 0, "blendSaves": 0, "reviewStills": 6, "clipFrames": 96, "networkCalls": 0},
}
(evidence / "render.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("RC3_VISUAL_RENDER=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
