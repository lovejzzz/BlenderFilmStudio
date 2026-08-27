import bpy
import hashlib
import json
import os
import stat
import struct
import time
from pathlib import Path
from mathutils import Vector

OUTPUT_ROOT = Path(os.environ["BFS_OUTPUT_ROOT"])
REPORT_PATH = Path(os.environ["BFS_REPORT_PATH"])
MILESTONE_PATH = Path(os.environ["BFS_MILESTONE_PATH"])
CONTROL_ID = os.environ["BFS_CONTROL_ID"]
ENGINE = os.environ["BFS_ENGINE"]
INVENTORY_PATHS = [
    "/usr/lib/x86_64-linux-gnu/dri/llvmpipe_dri.so",
    "/usr/lib/x86_64-linux-gnu/libEGL_mesa.so.0",
    "/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so",
    "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
    "/dev/dri",
]
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
    record = {"controlId": CONTROL_ID, "sequence": sequence, "name": name, "monotonicNs": time.monotonic_ns(), "processId": os.getpid(), "details": details or {}}
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


def inventory():
    result = []
    for raw in INVENTORY_PATHS:
        path = Path(raw)
        entry = {"path": raw, "exists": path.exists(), "type": None, "bytes": None}
        try:
            info = path.stat()
            entry["bytes"] = info.st_size
            entry["type"] = "directory" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other"
        except OSError:
            pass
        result.append(entry)
    return result


OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
milestone("PROCESS_STARTED")
capabilities = inventory()
milestone("INVENTORY_RECORDED", {"paths": capabilities})
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
cube = bpy.context.object
cube.name = "B41_D3_Canary_Cube"
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
scene.render.engine = ENGINE
if ENGINE == "CYCLES":
    scene.cycles.samples = int(os.environ["BFS_SAMPLES"])
    scene.cycles.device = "CPU"
scene.render.resolution_x = 32
scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.filepath = str(OUTPUT_ROOT / "canary.png")
scene.world.color = (0.025, 0.025, 0.025)
milestone("SCENE_CONFIGURED", {"engine": scene.render.engine, "samples": scene.cycles.samples if ENGINE == "CYCLES" else None})
blend_path = OUTPUT_ROOT / "canary.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
milestone("BLEND_SAVED", {"bytes": blend_path.stat().st_size, "sha256": sha256_file(blend_path)})
milestone("RENDER_STARTED")
bpy.ops.render.render(write_still=True)
png_path = OUTPUT_ROOT / "canary.png"
dimensions = png_dimensions(png_path)
milestone("RENDER_COMPLETED", {"bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions) if dimensions else None})
report = {
    "schemaVersion": "bfs.renderBackendControlCellReport.v0.1",
    "controlId": CONTROL_ID,
    "blender": {"versionTuple": list(bpy.app.version), "version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash), "renderEngine": scene.render.engine},
    "inventory": capabilities,
    "artifacts": {"blend": {"bytes": blend_path.stat().st_size, "sha256": sha256_file(blend_path)}, "png": {"bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions) if dimensions else None}},
    "passed": tuple(bpy.app.version) == (5, 2, 0) and scene.render.engine == ENGINE and dimensions == (32, 32),
}
REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
milestone("REPORT_WRITTEN", {"passed": report["passed"]})
print("BFS_B41_D3_CONTROL=" + ("PASS" if report["passed"] else "FAIL"), flush=True)
if not report["passed"]:
    raise SystemExit(1)
