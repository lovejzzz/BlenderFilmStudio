"""Render the frozen B20 history or single-frame process-isolation treatment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import bpy
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mode", choices=["history", "fresh"], required=True)
    parser.add_argument("--frame", type=int)
    parser.add_argument("--invocation-id", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_number(value: float) -> float:
    return round(float(value), 9)


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise RuntimeError(f"{label} mismatch: observed={observed!r} expected={expected!r}")


def camera_snapshot(scene: bpy.types.Scene, sample_frames: list[int]) -> dict[str, Any]:
    camera = scene.camera
    if camera is None:
        raise RuntimeError("Compiled scene has no active camera")
    original_frame = scene.frame_current
    samples = []
    for frame in sample_frames:
        scene.frame_set(frame)
        samples.append({
            "frame": frame,
            "location": [stable_number(value) for value in camera.location],
            "rotationEuler": [stable_number(value) for value in camera.rotation_euler],
            "matrixWorld": [stable_number(value) for row in camera.matrix_world for value in row],
            "lensMm": stable_number(camera.data.lens),
            "focusDistanceM": stable_number(camera.data.dof.focus_distance),
        })
    scene.frame_set(original_frame)
    action = camera.animation_data.action if camera.animation_data else None
    return {
        "scene": scene.name,
        "cameraObject": camera.name,
        "cameraData": camera.data.name,
        "cameraAction": action.name if action else None,
        "frameStart": scene.frame_start,
        "frameEnd": scene.frame_end,
        "fps": scene.render.fps,
        "fpsBase": stable_number(scene.render.fps_base),
        "samples": samples,
    }


def main() -> None:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    plan_path = Path.cwd() / receipt["executionIdentity"]["buildPlan"]["uri"]
    plan_wrapper = json.loads(plan_path.read_text(encoding="utf-8"))
    source = spec["source"]
    runtime = spec["runtime"]
    timeline = spec["timeline"]
    proxy = spec["proxy"]
    scene = bpy.context.scene

    require_equal(spec["documentType"], "BFS_REVIEW_RENDER_SPEC", "spec type")
    require_equal(proxy["classification"], "REVIEW_PROXY_NOT_MASTER", "proxy classification")
    require_equal(bpy.app.version_string, runtime["blender"]["version"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blender"]["buildHash"], "Blender build hash")
    require_equal(receipt["receiptHash"], source["receiptHash"], "receipt body hash")
    require_equal(receipt["executionIdentityHash"], source["executionIdentityHash"], "execution identity")
    require_equal(receipt["executionIdentity"]["buildPlan"]["planHash"], source["planHash"], "receipt plan hash")
    require_equal(receipt["run"]["sceneManifest"]["structureHash"], source["structureHash"], "receipt structure hash")
    require_equal(receipt["run"]["sceneBlend"]["sha256"], source["sceneBlendSha256"], "receipt scene hash")
    require_equal(sha256_file(Path(bpy.data.filepath)), source["sceneBlendSha256"], "opened scene bytes")
    require_equal(scene.get("bfs_plan_hash"), source["planHash"], "embedded plan marker")
    require_equal(scene.get("bfs_structure_hash"), source["structureHash"], "embedded structure marker")
    require_equal(scene.get("bfs_manifest_version"), "0.2.0", "embedded manifest version")
    require_equal(scene.get("bfs_ocio_sha256"), runtime["ocioConfigSha256"], "embedded OCIO marker")
    require_equal(ocio.GetCurrentConfig().getName(), plan_wrapper["plan"]["outputSpec"]["color"]["ocioConfigName"], "OCIO config name")
    require_equal(scene.frame_start, timeline["frameStart"], "frame start")
    require_equal(scene.frame_end, timeline["frameEnd"], "frame end")
    require_equal(scene.render.fps, timeline["fpsNumerator"], "fps numerator")
    require_equal(scene.render.fps_base, float(timeline["fpsDenominator"]), "fps denominator")

    if args.mode == "history":
        if args.frame is not None:
            raise RuntimeError("history mode must not receive --frame")
        requested_frames = list(range(timeline["frameStart"], timeline["frameEnd"] + 1))
    else:
        if args.frame is None or args.frame < timeline["frameStart"] or args.frame > timeline["frameEnd"]:
            raise RuntimeError("fresh mode requires one in-range --frame")
        requested_frames = [args.frame]

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B20 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    identity_before = camera_snapshot(scene, [timeline["frameStart"], 72, timeline["frameEnd"]])
    original_frame = scene.frame_current
    scene.render.engine = proxy["renderEngine"]
    scene.eevee.taa_render_samples = proxy["renderSamples"]
    scene.render.use_motion_blur = proxy["motionBlur"]
    scene.render.resolution_x = proxy["width"]
    scene.render.resolution_y = proxy["height"]
    scene.render.resolution_percentage = proxy["resolutionPercentage"]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = proxy["imageFormat"]
    scene.render.image_settings.color_mode = proxy["colorMode"]
    scene.render.image_settings.color_depth = proxy["colorDepth"]
    scene.render.film_transparent = proxy["filmTransparent"]
    scene.display_settings.display_device = proxy["display"]
    scene.view_settings.view_transform = proxy["view"]
    scene.view_settings.look = proxy["look"]
    scene.view_settings.exposure = proxy["exposure"]
    scene.view_settings.gamma = proxy["gamma"]
    scene.render.use_stamp = False

    observed_controls = {
        "renderSamples": int(scene.eevee.taa_render_samples),
        "ditherIntensity": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
    }
    require_equal(observed_controls, {
        "renderSamples": 32,
        "ditherIntensity": 0.0,
        "useFastGi": True,
        "useTaaReprojection": True,
    }, "B20 fixed controls")

    started = time.perf_counter()
    frames = []
    for frame in requested_frames:
        frame_started = time.perf_counter()
        scene.frame_set(frame)
        output = args.output_dir / f"frame-{frame:04d}.png"
        scene.render.filepath = str(output.resolve())
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not output.exists():
            raise RuntimeError(f"Frame {frame} render failed: {sorted(result)}")
        record = {
            "frame": frame,
            "name": output.name,
            "sha256": sha256_file(output),
            "bytes": output.stat().st_size,
            "renderSeconds": round(time.perf_counter() - frame_started, 6),
        }
        frames.append(record)
        print(f"BFS_B20_FRAME_OK {frame:04d} {record['sha256']} {record['renderSeconds']}")

    scene.frame_set(original_frame)
    identity_after = camera_snapshot(scene, [timeline["frameStart"], 72, timeline["frameEnd"]])
    require_equal(identity_after, identity_before, "camera/timeline identity after render")
    report = {
        "documentType": "BFS_B20_PROCESS_HISTORY_RENDER",
        "version": "0.1.0",
        "mode": args.mode,
        "invocationId": args.invocation_id,
        "processId": os.getpid(),
        "classification": proxy["classification"],
        "source": {
            "receiptHash": source["receiptHash"],
            "executionIdentityHash": source["executionIdentityHash"],
            "planHash": scene["bfs_plan_hash"],
            "structureHash": scene["bfs_structure_hash"],
            "sceneBlendSha256": sha256_file(Path(bpy.data.filepath)),
        },
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
            "renderEngine": scene.render.engine,
            "ocioConfigName": ocio.GetCurrentConfig().getName(),
        },
        "observedControls": observed_controls,
        "profile": proxy,
        "requestedFrames": requested_frames,
        "identityBefore": identity_before,
        "identityAfter": identity_after,
        "cameraAndTimelineInvariant": identity_before == identity_after,
        "frames": frames,
        "frameCount": len(frames),
        "totalFrameBytes": sum(frame["bytes"] for frame in frames),
        "totalRenderSeconds": round(time.perf_counter() - started, 6),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B20_RENDER_OK mode={args.mode} pid={os.getpid()} frames={len(frames)} seconds={report['totalRenderSeconds']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B20_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
