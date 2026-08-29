"""Zero-render Blender 5.2 configuration-surface probe for B62 Phase 0."""

from __future__ import annotations

import json

import bpy


def main() -> None:
    scene = bpy.context.scene
    scene.display_settings.display_device = "sRGB - Display"
    scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    old_look_rejected = False
    old_look_error = None
    try:
        scene.view_settings.look = "Medium High Contrast"
    except (TypeError, ValueError) as error:
        old_look_rejected = True
        old_look_error = f"{type(error).__name__}: {error}"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    color = {
        "display": scene.display_settings.display_device,
        "view": scene.view_settings.view_transform,
        "oldLookRejected": old_look_rejected,
        "oldLookError": old_look_error,
        "look": scene.view_settings.look,
        "exposure": scene.view_settings.exposure,
        "gamma": scene.view_settings.gamma,
    }

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 62001
    cycles = {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": scene.cycles.samples,
        "denoise": scene.cycles.use_denoising,
        "animatedSeed": scene.cycles.use_animated_seed,
        "seed": scene.cycles.seed,
    }

    scene.render.engine = "BLENDER_EEVEE_NEXT"
    if not hasattr(scene, "eevee"):
        raise RuntimeError("Scene.eevee missing")
    scene.eevee.taa_samples = 16
    scene.eevee.taa_render_samples = 16
    eevee = {"engine": scene.render.engine, "viewportSamples": scene.eevee.taa_samples, "renderSamples": scene.eevee.taa_render_samples}

    scene.render.use_motion_blur = True
    motion_blur = {"enabled": scene.render.use_motion_blur}

    settings = scene.render.image_settings
    settings.media_type = "MULTI_LAYER_IMAGE"
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_mode = "RGBA"
    settings.color_depth = "16"
    settings.exr_codec = "ZIP"
    exr = {"mediaType": settings.media_type, "fileFormat": settings.file_format, "colorMode": settings.color_mode, "colorDepth": settings.color_depth, "exrCodec": settings.exr_codec}

    record = {
        "schemaVersion": "bfs.b62Phase0D3Probe.v0.1",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "color": color,
        "cycles": cycles,
        "eevee": eevee,
        "motionBlur": motion_blur,
        "exr": exr,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }
    print("BFS_B62_D3_JSON " + json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
