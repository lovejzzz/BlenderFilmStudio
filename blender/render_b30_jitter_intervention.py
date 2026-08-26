"""Render the formal B30 NATURAL/CENTER fixed-jitter intervention cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import bpy
import PyOpenColorIO as ocio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b30-spec", type=Path, required=True)
    parser.add_argument("--review-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--replicate", required=True)
    parser.add_argument("--cell", choices=("NATURAL", "CENTER"), required=True)
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


def camera_snapshot(scene: bpy.types.Scene, frames: list[int]) -> dict[str, Any]:
    camera = scene.camera
    if camera is None:
        raise RuntimeError("Compiled scene has no active camera")
    original = scene.frame_current
    samples = []
    for frame in frames:
        scene.frame_set(frame)
        samples.append({
            "frame": frame,
            "location": [stable_number(value) for value in camera.location],
            "rotationEuler": [stable_number(value) for value in camera.rotation_euler],
            "matrixWorld": [stable_number(value) for row in camera.matrix_world for value in row],
            "lensMm": stable_number(camera.data.lens),
            "focusDistanceM": stable_number(camera.data.dof.focus_distance),
        })
    scene.frame_set(original)
    return {
        "scene": scene.name,
        "cameraObject": camera.name,
        "cameraData": camera.data.name,
        "frameStart": scene.frame_start,
        "frameEnd": scene.frame_end,
        "fps": scene.render.fps,
        "fpsBase": stable_number(scene.render.fps_base),
        "samples": samples,
    }


def property_value(scene: bpy.types.Scene) -> list[float] | None:
    if "override_pixel_jitter_sample" not in scene:
        return None
    value = scene["override_pixel_jitter_sample"]
    return [stable_number(value[0]), stable_number(value[1])]


def main() -> None:
    args = parse_args()
    spec = json.loads(args.b30_spec.read_text(encoding="utf-8"))
    review = json.loads(args.review_spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require_equal(spec["documentType"], "BFS_FIXED_JITTER_INTERVENTION_SPEC", "B30 spec type")
    require_equal(spec["status"], "pre-registered", "B30 status")
    require_equal(review["documentType"], "BFS_REVIEW_RENDER_SPEC", "review spec type")
    expected_prefix = "N" if args.cell == "NATURAL" else "C"
    if re.fullmatch(rf"{expected_prefix}(0[1-9]|1[0-2])", args.replicate) is None:
        raise RuntimeError(f"Invalid {args.cell} replicate {args.replicate!r}")

    scene = bpy.context.scene
    source, runtime, timeline, proxy = review["source"], review["runtime"], review["timeline"], review["proxy"]
    plan_path = Path.cwd() / receipt["executionIdentity"]["buildPlan"]["uri"]
    plan_wrapper = json.loads(plan_path.read_text(encoding="utf-8"))
    require_equal(proxy["classification"], "REVIEW_PROXY_NOT_MASTER", "proxy classification")
    require_equal(bpy.app.version_string, runtime["blender"]["version"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blender"]["buildHash"], "Blender build hash")
    require_equal(receipt["receiptHash"], source["receiptHash"], "receipt hash")
    require_equal(receipt["executionIdentityHash"], source["executionIdentityHash"], "execution identity")
    require_equal(receipt["executionIdentity"]["buildPlan"]["planHash"], source["planHash"], "plan hash")
    require_equal(receipt["run"]["sceneManifest"]["structureHash"], source["structureHash"], "structure hash")
    require_equal(receipt["run"]["sceneBlend"]["sha256"], source["sceneBlendSha256"], "scene receipt hash")
    require_equal(sha256_file(Path(bpy.data.filepath)), source["sceneBlendSha256"], "opened scene bytes")
    require_equal(scene.get("bfs_plan_hash"), source["planHash"], "embedded plan marker")
    require_equal(scene.get("bfs_structure_hash"), source["structureHash"], "embedded structure marker")
    require_equal(scene.get("bfs_ocio_sha256"), runtime["ocioConfigSha256"], "embedded OCIO marker")
    require_equal(ocio.GetCurrentConfig().getName(), plan_wrapper["plan"]["outputSpec"]["color"]["ocioConfigName"], "OCIO config name")
    require_equal(scene.frame_start, timeline["frameStart"], "frame start")
    require_equal(scene.frame_end, timeline["frameEnd"], "frame end")
    require_equal(scene.render.fps, timeline["fpsNumerator"], "fps")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B30 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    identity_before = camera_snapshot(scene, [1, 38, 72, 144])
    original_frame = scene.frame_current
    property_before = property_value(scene)
    if args.cell == "NATURAL":
        if "override_pixel_jitter_sample" in scene:
            del scene["override_pixel_jitter_sample"]
        expected_property = None
    else:
        scene["override_pixel_jitter_sample"] = [0.0, 0.0]
        expected_property = [0.0, 0.0]
    property_after = property_value(scene)
    require_equal(property_after, expected_property, "jitter intervention")

    scene.render.engine = proxy["renderEngine"]
    scene.eevee.taa_render_samples = proxy["renderSamples"]
    scene.render.use_motion_blur = proxy["motionBlur"]
    scene.render.resolution_x, scene.render.resolution_y = proxy["width"], proxy["height"]
    scene.render.resolution_percentage = proxy["resolutionPercentage"]
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = proxy["imageFormat"]
    scene.render.image_settings.color_mode = proxy["colorMode"]
    scene.render.image_settings.color_depth = proxy["colorDepth"]
    scene.render.film_transparent = proxy["filmTransparent"]
    scene.display_settings.display_device = proxy["display"]
    scene.view_settings.view_transform, scene.view_settings.look = proxy["view"], proxy["look"]
    scene.view_settings.exposure, scene.view_settings.gamma = proxy["exposure"], proxy["gamma"]
    scene.render.use_stamp = False
    observed_controls = {
        "threadsMode": scene.render.threads_mode,
        "threads": int(scene.render.threads),
        "renderSamples": int(scene.eevee.taa_render_samples),
        "ditherIntensity": float(scene.render.dither_intensity),
        "useFastGi": bool(scene.eevee.use_fast_gi),
        "useTaaReprojection": bool(scene.eevee.use_taa_reprojection),
        "motionBlur": bool(scene.render.use_motion_blur),
    }
    constants = spec["constants"]
    require_equal(observed_controls, {
        "threadsMode": constants["threadsMode"], "threads": constants["threads"],
        "renderSamples": constants["renderSamples"], "ditherIntensity": constants["ditherIntensity"],
        "useFastGi": constants["useFastGi"], "useTaaReprojection": constants["useTaaReprojection"],
        "motionBlur": constants["motionBlur"],
    }, "frozen controls")

    target = spec["design"]["targetFrame"]
    calls = spec["design"]["renderCallsPerProcess"]
    scene.frame_set(target)
    started = time.perf_counter()
    outputs = []
    for ordinal in range(1, calls + 1):
        require_equal(scene.frame_current, target, f"frame before call {ordinal}")
        require_equal(property_value(scene), expected_property, f"jitter property before call {ordinal}")
        output = args.output_dir / f"call-{ordinal:02d}.png"
        scene.render.filepath = str(output.resolve())
        call_started = time.perf_counter()
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not output.exists():
            raise RuntimeError(f"Render {ordinal} failed: {sorted(result)}")
        require_equal(scene.frame_current, target, f"frame after call {ordinal}")
        require_equal(property_value(scene), expected_property, f"jitter property after call {ordinal}")
        item = {
            "callOrdinal": ordinal, "frame": target, "name": output.name,
            "sha256": sha256_file(output), "bytes": output.stat().st_size,
            "renderSeconds": round(time.perf_counter() - call_started, 6),
        }
        outputs.append(item)
        print(f"BFS_B30_RENDER_CALL_OK {args.replicate} {ordinal:02d} {item['sha256']}")

    scene.frame_set(original_frame)
    identity_after = camera_snapshot(scene, [1, 38, 72, 144])
    require_equal(identity_after, identity_before, "camera/timeline identity after renders")
    report = {
        "documentType": "BFS_B30_JITTER_INTERVENTION_RENDER", "version": "0.1.0",
        "b30SpecSha256": sha256_file(args.b30_spec), "replicate": args.replicate, "cell": args.cell,
        "processId": os.getpid(), "classification": proxy["classification"],
        "source": {"receiptHash": source["receiptHash"], "executionIdentityHash": source["executionIdentityHash"],
                   "planHash": scene["bfs_plan_hash"], "structureHash": scene["bfs_structure_hash"],
                   "sceneBlendSha256": sha256_file(Path(bpy.data.filepath))},
        "runtime": {"blenderVersion": bpy.app.version_string, "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
                    "renderEngine": scene.render.engine, "ocioConfigName": ocio.GetCurrentConfig().getName()},
        "profile": proxy, "observedControls": observed_controls,
        "intervention": {"property": "override_pixel_jitter_sample", "before": property_before,
                         "after": property_after, "expected": expected_property},
        "identityBefore": identity_before, "identityAfter": identity_after,
        "cameraAndTimelineInvariant": identity_before == identity_after,
        "targetFrame": target, "frameSetCountBeforeRenders": 1, "frameAfterSet": target,
        "renderOperatorCallCount": len(outputs), "callOrder": [item["callOrdinal"] for item in outputs],
        "frameObservedEveryCall": all(item["frame"] == target for item in outputs),
        "outputs": outputs, "outputFileCount": len(outputs), "totalBytes": sum(item["bytes"] for item in outputs),
        "totalRenderSeconds": round(time.perf_counter() - started, 6), "savedSourceBlend": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B30_PROCESS_RENDER_OK {args.replicate} cell={args.cell} calls={len(outputs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B30_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
