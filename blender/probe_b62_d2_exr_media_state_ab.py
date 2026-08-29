"""Repeated zero-render A/B/A setter probe for Blender 5.2 multilayer EXR."""

from __future__ import annotations

import json

import bpy


def attempt(settings: bpy.types.ImageFormatSettings, repetition: int, phase: str, media_type: str, expect_accept: bool) -> dict:
    settings.media_type = media_type
    before = settings.file_format
    accepted = True
    error = None
    try:
        settings.file_format = "OPEN_EXR_MULTILAYER"
    except (TypeError, ValueError) as exception:
        accepted = False
        error = f"{type(exception).__name__}: {exception}"
    return {
        "repetition": repetition,
        "phase": phase,
        "mediaType": settings.media_type,
        "fileFormatBefore": before,
        "accepted": accepted,
        "expectedAccepted": expect_accept,
        "outcomeExact": accepted is expect_accept,
        "fileFormatAfter": settings.file_format,
        "error": error,
    }


def main() -> None:
    settings = bpy.context.scene.render.image_settings
    rows = []
    for repetition in range(1, 4):
        rows.append(attempt(settings, repetition, "A1_IMAGE_REJECT", "IMAGE", False))
        rows.append(attempt(settings, repetition, "B_MULTI_ACCEPT", "MULTI_LAYER_IMAGE", True))
        rows.append(attempt(settings, repetition, "A2_IMAGE_REJECT", "IMAGE", False))
    settings.media_type = "MULTI_LAYER_IMAGE"
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_mode = "RGBA"
    settings.color_depth = "16"
    settings.exr_codec = "ZIP"
    record = {
        "schemaVersion": "bfs.b62Phase0D2Probe.v0.1",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "rows": rows,
        "final": {"mediaType": settings.media_type, "fileFormat": settings.file_format, "colorMode": settings.color_mode, "colorDepth": settings.color_depth, "exrCodec": settings.exr_codec},
        "decisionUsesEnumItems": False,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }
    print("BFS_B62_D2_JSON " + json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
