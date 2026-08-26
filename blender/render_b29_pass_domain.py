"""Formal B29 renderer: repeated frame 38 with PNG8 and multilayer EXR32 saves."""

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
    parser.add_argument("--b29-spec", type=Path, required=True)
    parser.add_argument("--review-spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--replicate", required=True)
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


def camera_snapshot(scene: bpy.types.Scene) -> dict[str, Any]:
    camera = scene.camera
    if camera is None:
        raise RuntimeError("No active camera")
    original = scene.frame_current
    samples = []
    for frame in (1, 38, 72, 144):
        scene.frame_set(frame)
        samples.append({"frame": frame, "matrixWorld": [stable_number(value) for row in camera.matrix_world for value in row], "lensMm": stable_number(camera.data.lens), "focusDistanceM": stable_number(camera.data.dof.focus_distance)})
    scene.frame_set(original)
    return {"cameraObject": camera.name, "cameraData": camera.data.name, "frameStart": scene.frame_start, "frameEnd": scene.frame_end, "fps": scene.render.fps, "samples": samples}


def main() -> None:
    args = parse_args()
    spec = json.loads(args.b29_spec.read_text(encoding="utf-8"))
    review = json.loads(args.review_spec.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    layer = scene.view_layers[0]
    require_equal(spec["documentType"], "BFS_PASS_DOMAIN_LOCALIZATION_SPEC", "B29 spec type")
    require_equal(spec["status"], "pre-registered", "B29 status")
    if re.fullmatch(r"P(0[1-9]|1[0-2])", args.replicate) is None:
        raise RuntimeError(f"Invalid replicate {args.replicate}")
    source, runtime, timeline, proxy = review["source"], review["runtime"], review["timeline"], review["proxy"]
    plan_path = Path.cwd() / receipt["executionIdentity"]["buildPlan"]["uri"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))["plan"]
    require_equal(bpy.app.version_string, runtime["blender"]["version"], "Blender version")
    require_equal(bpy.app.build_hash.decode("utf-8"), runtime["blender"]["buildHash"], "Blender build")
    require_equal(receipt["receiptHash"], source["receiptHash"], "receipt")
    require_equal(receipt["executionIdentityHash"], source["executionIdentityHash"], "execution identity")
    require_equal(sha256_file(Path(bpy.data.filepath)), source["sceneBlendSha256"], "scene bytes")
    require_equal(scene.get("bfs_plan_hash"), source["planHash"], "plan marker")
    require_equal(scene.get("bfs_structure_hash"), source["structureHash"], "structure marker")
    require_equal(scene.get("bfs_ocio_sha256"), runtime["ocioConfigSha256"], "OCIO marker")
    require_equal(ocio.GetCurrentConfig().getName(), plan["outputSpec"]["color"]["ocioConfigName"], "OCIO name")
    require_equal([scene.frame_start, scene.frame_end, scene.render.fps], [timeline["frameStart"], timeline["frameEnd"], timeline["fpsNumerator"]], "timeline")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise RuntimeError("B29 output directory must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    before = camera_snapshot(scene)
    original_frame = scene.frame_current
    scene.render.engine = proxy["renderEngine"]
    scene.eevee.taa_render_samples = proxy["renderSamples"]
    scene.render.use_motion_blur = proxy["motionBlur"]
    scene.render.resolution_x, scene.render.resolution_y = proxy["width"], proxy["height"]
    scene.render.resolution_percentage = proxy["resolutionPercentage"]
    scene.render.film_transparent = proxy["filmTransparent"]
    scene.display_settings.display_device = proxy["display"]
    scene.view_settings.view_transform, scene.view_settings.look = proxy["view"], proxy["look"]
    scene.view_settings.exposure, scene.view_settings.gamma = proxy["exposure"], proxy["gamma"]
    scene.render.use_stamp = False
    layer.use_pass_combined = True
    layer.use_pass_z = True
    layer.use_pass_normal = True
    layer.use_pass_position = True
    layer.use_pass_vector = True
    layer.use_pass_cryptomatte_object = True
    layer.pass_cryptomatte_depth = 6
    require_equal(layer.use_pass_cryptomatte_accurate, True, "source accurate cryptomatte")
    pass_state = {"viewLayer": layer.name, "Combined": layer.use_pass_combined, "Depth": layer.use_pass_z, "Normal": layer.use_pass_normal, "Position": layer.use_pass_position, "Vector": layer.use_pass_vector, "CryptoObject": layer.use_pass_cryptomatte_object, "cryptomatteDepth": layer.pass_cryptomatte_depth, "cryptomatteAccurate": layer.use_pass_cryptomatte_accurate}
    controls = {"threadsMode": scene.render.threads_mode, "threads": scene.render.threads, "renderSamples": scene.eevee.taa_render_samples, "ditherIntensity": scene.render.dither_intensity, "useFastGi": scene.eevee.use_fast_gi, "useTaaReprojection": scene.eevee.use_taa_reprojection, "motionBlur": scene.render.use_motion_blur}
    frozen = spec["constants"]
    require_equal(controls, {"threadsMode": frozen["threadsMode"], "threads": frozen["threads"], "renderSamples": frozen["renderSamples"], "ditherIntensity": frozen["ditherIntensity"], "useFastGi": frozen["useFastGi"], "useTaaReprojection": frozen["useTaaReprojection"], "motionBlur": frozen["motionBlur"]}, "controls")

    scene.frame_set(spec["design"]["targetFrame"])
    outputs = []
    for ordinal in range(1, spec["design"]["renderCallsPerProcess"] + 1):
        if scene.frame_current != 38:
            raise RuntimeError(f"Frame changed before call {ordinal}")
        started = time.perf_counter()
        scene.render.image_settings.media_type = "IMAGE"
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "8"
        result = bpy.ops.render.render(write_still=False)
        if "FINISHED" not in result:
            raise RuntimeError(f"Render {ordinal} failed: {sorted(result)}")
        render_result = bpy.data.images.get("Render Result")
        if render_result is None:
            raise RuntimeError("Render Result missing")
        png = args.output_dir / f"render-{ordinal:02d}.png"
        render_result.save_render(str(png.resolve()), scene=scene)
        scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
        scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "32"
        scene.render.image_settings.exr_codec = "ZIP"
        exr = args.output_dir / f"render-{ordinal:02d}.exr"
        render_result.save_render(str(exr.resolve()), scene=scene)
        if not png.exists() or not exr.exists() or scene.frame_current != 38:
            raise RuntimeError(f"Call {ordinal} save/frame contract failed")
        outputs.append({"callOrdinal": ordinal, "frame": 38, "renderOperatorCalls": 1, "sameRenderResultSaveCount": 2, "png": {"name": png.name, "sha256": sha256_file(png), "bytes": png.stat().st_size}, "exr": {"name": exr.name, "sha256": sha256_file(exr), "bytes": exr.stat().st_size}, "seconds": round(time.perf_counter() - started, 6)})
        print(f"BFS_B29_RENDER_CALL_OK {args.replicate} {ordinal:02d} png={outputs[-1]['png']['sha256']} exr={outputs[-1]['exr']['sha256']}")
    scene.frame_set(original_frame)
    after = camera_snapshot(scene)
    require_equal(after, before, "camera/timeline invariant")
    report = {"documentType": "BFS_B29_PASS_DOMAIN_RENDER", "version": "0.1.0", "b29SpecSha256": sha256_file(args.b29_spec), "replicate": args.replicate, "processId": os.getpid(), "source": {"sceneBlendSha256": sha256_file(Path(bpy.data.filepath)), "planHash": scene["bfs_plan_hash"], "structureHash": scene["bfs_structure_hash"]}, "runtime": {"blenderVersion": bpy.app.version_string, "blenderBuildHash": bpy.app.build_hash.decode("utf-8"), "ocioConfigName": ocio.GetCurrentConfig().getName()}, "controls": controls, "passState": pass_state, "targetFrame": 38, "frameSetCountBeforeRenders": 1, "renderOperatorCallCount": len(outputs), "saveCount": len(outputs) * 2, "sameRenderResultForEveryPngExrPair": True, "callOrder": [item["callOrdinal"] for item in outputs], "outputs": outputs, "cameraAndTimelineInvariant": before == after, "savedSourceBlend": False}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B29_PROCESS_RENDER_OK {args.replicate} pid={os.getpid()} calls={len(outputs)} saves={len(outputs)*2}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B29_RENDER_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
