import bpy
import hashlib
import json
import os
import struct
import time
from pathlib import Path
from mathutils import Vector

OUTPUT_ROOT = Path(os.environ["BFS_OUTPUT_ROOT"])
REPORT_PATH = Path(os.environ["BFS_REPORT_PATH"])
MILESTONE_PATH = Path(os.environ["BFS_MILESTONE_PATH"])
CELL_ID = os.environ["BFS_CELL_ID"]
sequence = 0


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def milestone(name, details=None):
    global sequence
    sequence += 1
    record = {
        "cellId": CELL_ID,
        "sequence": sequence,
        "name": name,
        "monotonicNs": time.monotonic_ns(),
        "processId": os.getpid(),
        "details": details or {},
    }
    with open(MILESTONE_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def png_dimensions(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
milestone("PROCESS_STARTED")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
cube = bpy.context.object
cube.name = "B41_D2_Canary_Cube"
bpy.ops.object.camera_add(location=(4.0, -4.0, 3.0))
camera = bpy.context.object
point_at(camera, (0.0, 0.0, 0.0))
bpy.context.scene.camera = camera
bpy.ops.object.light_add(type="AREA", location=(2.0, -2.0, 4.0))
light = bpy.context.object
light.data.energy = 900.0
light.data.shape = "DISK"
light.data.size = 4.0
point_at(light, (0.0, 0.0, 0.0))
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 32
scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False
scene.render.filepath = str(OUTPUT_ROOT / "canary.png")
scene.world.color = (0.025, 0.025, 0.025)
milestone("SCENE_CONFIGURED", {"engine": scene.render.engine})
blend_path = OUTPUT_ROOT / "canary.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
milestone("BLEND_SAVED", {"bytes": blend_path.stat().st_size, "sha256": sha256_file(blend_path)})
milestone("GPU_PROBE_STARTED")
gpu_identity = {}
try:
    import gpu
    for label, name in [
        ("backend", "backend_type_get"),
        ("device", "device_type_get"),
        ("vendor", "vendor_get"),
        ("renderer", "renderer_get"),
        ("version", "version_get"),
    ]:
        function = getattr(gpu.platform, name, None)
        gpu_identity[label] = function() if function else None
except Exception as error:
    gpu_identity["error"] = f"{type(error).__name__}: {error}"
milestone("GPU_PROBE_COMPLETED", gpu_identity)
milestone("RENDER_STARTED")
bpy.ops.render.render(write_still=True)
png_path = OUTPUT_ROOT / "canary.png"
dimensions = png_dimensions(png_path)
milestone("RENDER_COMPLETED", {"bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions) if dimensions else None})
report = {
    "schemaVersion": "bfs.eeveeHeadlessDiagnosticCellReport.v0.1",
    "cellId": CELL_ID,
    "blender": {"versionTuple": list(bpy.app.version), "version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), "renderEngine": scene.render.engine},
    "gpu": gpu_identity,
    "artifacts": {"blend": {"bytes": blend_path.stat().st_size, "sha256": sha256_file(blend_path)}, "png": {"bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions) if dimensions else None}},
    "passed": tuple(bpy.app.version) == (5, 2, 0) and scene.render.engine == "BLENDER_EEVEE" and dimensions == (32, 32),
}
REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
milestone("REPORT_WRITTEN", {"passed": report["passed"]})
print("BFS_B41_D2_CELL=" + ("PASS" if report["passed"] else "FAIL"), flush=True)
if not report["passed"]:
    raise SystemExit(1)
