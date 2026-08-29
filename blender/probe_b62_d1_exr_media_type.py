"""Zero-render Blender 5.2 probe for ImageFormatSettings media-type ordering."""

from __future__ import annotations

import json

import bpy


def enum_values(settings: bpy.types.ImageFormatSettings, property_name: str) -> list[str]:
    return [item.identifier for item in settings.bl_rna.properties[property_name].enum_items]


def main() -> None:
    settings = bpy.context.scene.render.image_settings
    default = {
        "mediaType": settings.media_type,
        "fileFormat": settings.file_format,
        "fileFormatEnums": enum_values(settings, "file_format"),
    }
    rejected_before_media_type = False
    rejection = None
    try:
        settings.file_format = "OPEN_EXR_MULTILAYER"
    except (TypeError, ValueError) as error:
        rejected_before_media_type = True
        rejection = f"{type(error).__name__}: {error}"
    settings.media_type = "MULTI_LAYER_IMAGE"
    after_media_type = {
        "mediaType": settings.media_type,
        "fileFormatBeforeAssignment": settings.file_format,
        "fileFormatEnums": enum_values(settings, "file_format"),
    }
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_mode = "RGBA"
    settings.color_depth = "16"
    settings.exr_codec = "ZIP"
    final = {
        "mediaType": settings.media_type,
        "fileFormat": settings.file_format,
        "colorMode": settings.color_mode,
        "colorDepth": settings.color_depth,
        "exrCodec": settings.exr_codec,
    }
    record = {
        "schemaVersion": "bfs.b62Phase0D1Probe.v0.1",
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii")},
        "default": default,
        "assignmentBeforeMediaTypeRejected": rejected_before_media_type,
        "assignmentBeforeMediaTypeError": rejection,
        "afterMediaType": after_media_type,
        "final": final,
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }
    print("BFS_B62_D1_JSON " + json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
