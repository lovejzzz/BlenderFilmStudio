import bpy
import hashlib
import json
import math
import os
import socket
import struct
import sys
from pathlib import Path
from mathutils import Vector

OUTPUT_ROOT = Path(os.environ["BFS_OUTPUT_ROOT"])
REPORT_PATH = Path(os.environ["BFS_REPORT_PATH"])


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proc_status():
    values = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key] = value.strip()
    return values


def cgroup_value(name):
    return Path("/sys/fs/cgroup", name).read_text().strip()


def denied_write(path):
    try:
        Path(path).write_text("must-not-write", encoding="utf-8")
        return False
    except OSError:
        return True


def network_denied():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1.0)
    try:
        return probe.connect_ex(("1.1.1.1", 53)) != 0
    finally:
        probe.close()


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def png_dimensions(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
output_probe = OUTPUT_ROOT / "output-write-canary.txt"
output_probe.write_text("writable", encoding="utf-8")
status = proc_status()
executable = "/opt/bfs/blender/blender"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
cube = bpy.context.object
cube.name = "B41_Canary_Cube"

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
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 32
scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False
scene.render.filepath = str(OUTPUT_ROOT / "canary.png")
scene.world.color = (0.025, 0.025, 0.025)

blend_path = OUTPUT_ROOT / "canary.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
bpy.ops.render.render(write_still=True)

png_path = OUTPUT_ROOT / "canary.png"
dimensions = png_dimensions(png_path)
checks = {
    "blenderVersionExact": tuple(bpy.app.version) == (5, 2, 0),
    "blenderExecutableSha256": sha256_file(executable) == "83e8261eace07a5337f71b52d156c1eece1a6ba913403cc6406182ae58bacf27",
    "uidNonRootExact": os.geteuid() == 65532 and os.getegid() == 65532,
    "capabilitiesEmpty": status.get("CapEff") == "0000000000000000",
    "noNewPrivileges": status.get("NoNewPrivs") == "1",
    "parentSecretAbsent": "BFS_PARENT_SECRET" not in os.environ,
    "inputWriteDenied": denied_write("/inputs/forbidden-write.txt"),
    "rootWriteDenied": denied_write("/forbidden-root-write.txt"),
    "outputWriteAccepted": output_probe.read_text(encoding="utf-8") == "writable",
    "networkDenied": network_denied(),
    "pidsLimitExact": cgroup_value("pids.max") == "256",
    "memoryLimitExact": cgroup_value("memory.max") == "8589934592",
    "cpuLimitExact": cgroup_value("cpu.max") == "400000 100000",
    "onlineAccessDisabled": getattr(bpy.app, "online_access", None) is False,
    "autoexecDisabled": bpy.context.preferences.filepaths.use_scripts_auto_execute is False,
    "requiredArgvPresent": all(flag in sys.argv for flag in ["--background", "--factory-startup", "--disable-autoexec", "--offline-mode", "--python-exit-code"]),
    "blendSaved": blend_path.is_file() and blend_path.stat().st_size > 0,
    "eeveeRenderValid": dimensions == (32, 32),
}
report = {
    "schemaVersion": "bfs.blenderRuntimeCanaryReport.v0.1",
    "jobId": os.environ["BFS_JOB_ID"],
    "blender": {
        "version": bpy.app.version_string,
        "versionTuple": list(bpy.app.version),
        "buildHash": bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "buildPlatform": bpy.app.build_platform.decode() if isinstance(bpy.app.build_platform, bytes) else str(bpy.app.build_platform),
        "executable": executable,
        "executableSha256": sha256_file(executable),
        "renderEngine": scene.render.engine,
    },
    "process": {"uid": os.geteuid(), "gid": os.getegid(), "capEff": status.get("CapEff"), "noNewPrivs": status.get("NoNewPrivs")},
    "cgroup": {"pidsMax": cgroup_value("pids.max"), "memoryMax": cgroup_value("memory.max"), "cpuMax": cgroup_value("cpu.max")},
    "artifacts": {
        "blend": {"path": str(blend_path), "bytes": blend_path.stat().st_size, "sha256": sha256_file(blend_path)},
        "png": {"path": str(png_path), "bytes": png_path.stat().st_size, "sha256": sha256_file(png_path), "dimensions": list(dimensions) if dimensions else None},
    },
    "checks": checks,
    "passed": all(checks.values()),
}
REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("BFS_B41_RUNTIME_CANARY=" + ("PASS" if report["passed"] else "FAIL"), flush=True)
if not report["passed"]:
    raise SystemExit(1)
