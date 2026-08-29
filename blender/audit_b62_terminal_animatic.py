"""Independently audit the preregistered B62 terminal animatic without rendering."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import OpenImageIO as oiio
import bpy
import numpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


EXPERIMENT_ID = "B62-T2-E1"
SCENE_SHA256 = "0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc"
CAMERAS = ((1, 96, "SHOT_WIDE_APPROACH", "CAM_WIDE_APPROACH"), (97, 192, "SHOT_MEDIUM_CONTACT", "CAM_MEDIUM_CONTACT"), (193, 288, "SHOT_CLOSE_REFLECTION", "CAM_CLOSE_MOTION_TERMINAL"))
STATE_FRAMES = (138, 143, 144, 150, 288)
ANCHORS = ("B62_VISOR", "B62_EYE_SLIT", "B62_CHEST_LIGHT", "B62_HAND_R", "B62_CORE")
FACE_ANCHORS = {"B62_VISOR", "B62_EYE_SLIT"}
CHARACTER = {
    "B62_CHEST_LIGHT", "B62_CHEST_PLATE", "B62_EYE_SLIT", "B62_FOOT_L", "B62_FOOT_R",
    "B62_FOREARM_L", "B62_FOREARM_R", "B62_HAND_L", "B62_HAND_R", "B62_HELMET", "B62_NECK",
    "B62_PELVIS", "B62_SHIN_L", "B62_SHIN_R", "B62_SHOULDER_L", "B62_SHOULDER_R",
    "B62_THIGH_L", "B62_THIGH_R", "B62_TORSO", "B62_UPPER_ARM_L", "B62_UPPER_ARM_R", "B62_VISOR",
}
CORE = {"B62_CORE", "B62_CORE_RING_A", "B62_CORE_RING_B"}


def arguments():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--render-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    return parser.parse_args(tail)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, float) and math.isfinite(value):
        return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(child) for key, child in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def valid_self(document, field):
    expected = document.get(field)
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    body = dict(document)
    del body[field]
    return hashlib.sha256(canonical(body)).hexdigest() == expected


def write_hashed(path, body):
    require(not path.exists(), f"output exists {path}")
    document = {**body, "reportHash": hashlib.sha256(canonical(body)).hexdigest()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return document


def expected_route(frame):
    return next((marker, camera) for start, end, marker, camera in CAMERAS if start <= frame <= end)


def object_group(name):
    if name in CHARACTER:
        return "CHARACTER"
    if name in CORE:
        return "CORE"
    if name.startswith("B62_"):
        return "SCENE_OR_PROP"
    return "OTHER"


def material_state(owner):
    owner = getattr(owner, "original", None) or owner
    rows = []
    for material in [item for item in getattr(getattr(owner, "data", None), "materials", []) if item]:
        outputs = [node for node in material.node_tree.nodes if node.type == "OUTPUT_MATERIAL"] if material.use_nodes and material.node_tree else []
        rows.append({
            "outputs": len(outputs),
            "surface": any(node.inputs.get("Surface") and node.inputs["Surface"].is_linked for node in outputs),
            "volume": any(node.inputs.get("Volume") and node.inputs["Volume"].is_linked for node in outputs),
        })
    passthrough = bool(rows) and all(row["outputs"] and row["volume"] and not row["surface"] for row in rows)
    return owner.name, passthrough


def trace(scene, depsgraph, origin, heading, maximum):
    direction = heading.normalized()
    cursor = origin.copy()
    travelled = 0.0
    for _ in range(64):
        remaining = maximum - travelled
        if remaining <= 0:
            return None, "MISS", False
        hit, location, _normal, _face, owner, _matrix = scene.ray_cast(depsgraph, cursor, direction, distance=remaining)
        if not hit or owner is None:
            return None, "MISS", False
        distance = float((location - cursor).length)
        name, passthrough = material_state(owner)
        if passthrough:
            travelled += distance + 0.00001
            cursor = location + direction * 0.00001
            continue
        return name, object_group(name), False
    return None, "MISS", True


def object_center(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    return sum((evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box), Vector()) / len(evaluated.bound_box)


def character_projection(scene, depsgraph, camera):
    total = 0
    on_screen = 0
    points = []
    for name in sorted(CHARACTER):
        evaluated = bpy.data.objects[name].evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
        try:
            for vertex in mesh.vertices:
                total += 1
                point = world_to_camera_view(scene, camera, evaluated.matrix_world @ vertex.co)
                if point.z > 0:
                    points.append((float(point.x), float(point.y)))
                    on_screen += int(0 <= point.x <= 1 and 0 <= point.y <= 1)
        finally:
            evaluated.to_mesh_clear()
    require(points and total > 0, "empty character projection")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    area = max(0, min(1, max(xs)) - max(0, min(xs))) * max(0, min(1, max(ys)) - max(0, min(ys)))
    return {
        "totalVertices": total,
        "onScreenVertices": on_screen,
        "onScreenVertexFraction": on_screen / total,
        "clampedUnionAreaFraction": area,
    }


def geometry(scene, frame, camera):
    scene.frame_set(frame)
    scene.camera = camera
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = camera.evaluated_get(depsgraph)
    corners = evaluated.data.view_frame(scene=scene)
    left, right = min(corner.x for corner in corners), max(corner.x for corner in corners)
    bottom, top = min(corner.y for corner in corners), max(corner.y for corner in corners)
    z = sum(corner.z for corner in corners) / 4
    origin = evaluated.matrix_world.translation.copy()
    rotation = evaluated.matrix_world.to_quaternion()
    counts = {}
    groups = {"CHARACTER": 0, "CORE": 0, "SCENE_OR_PROP": 0, "OTHER": 0, "MISS": 0}
    for index in range(32 * 18):
        y, x = divmod(index, 32)
        u, v = (x + 0.5) / 32, (y + 0.5) / 18
        local = Vector((left + (right - left) * u, bottom + (top - bottom) * v, z))
        name, group, exhausted = trace(scene, depsgraph, origin, rotation @ local, 1000)
        require(not exhausted, f"ray traversal exhausted at frame {frame}")
        groups[group] += 1
        if name:
            counts[name] = counts.get(name, 0) + 1
    visible = []
    for anchor in ANCHORS:
        point = object_center(bpy.data.objects[anchor], depsgraph)
        name, _group, exhausted = trace(scene, depsgraph, origin, point - origin, (point - origin).length + 0.01)
        require(not exhausted, f"anchor traversal exhausted at frame {frame}")
        if name == anchor:
            visible.append(anchor)
    projection = character_projection(scene, depsgraph, evaluated)
    helmet_share = counts.get("B62_HELMET", 0) / 576
    character_share = groups["CHARACTER"] / 576
    feasible = (
        FACE_ANCHORS.issubset(visible)
        and helmet_share <= 0.7
        and 0.2 <= character_share <= 0.9
        and 0.1 <= projection["onScreenVertexFraction"] <= 0.6
        and 0.35 <= projection["clampedUnionAreaFraction"] <= 0.9
        and len(visible) >= 2
    )
    return {
        "frame": frame,
        "camera": camera.name,
        "objectCounts": dict(sorted(counts.items())),
        "groupCounts": groups,
        "helmetVisualBlockerShare": helmet_share,
        "characterVisualBlockerShare": character_share,
        "visibleAnchors": visible,
        "visibleAnchorCount": len(visible),
        "characterProjection": projection,
        "feasible": feasible,
    }


def decode_png(path):
    require(oiio.VERSION_STRING == "3.1.13.1" and numpy.__version__ == "2.3.4", "decoder version mismatch")
    image = oiio.ImageInput.open(str(path))
    require(image is not None, f"PNG open failed {path.name}")
    try:
        spec = image.spec()
        names = list(spec.channelnames)
        positions = {name: index for index, name in enumerate(names)}
        require(all(channel in positions for channel in "RGBA"), f"RGBA channels absent {path.name}: {names}")
        pixels = image.read_image(oiio.FLOAT)
        values = numpy.ascontiguousarray(numpy.asarray(pixels)[..., [positions[channel] for channel in "RGBA"]], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(values)
        rgb = values[..., :3]
        finite_rgb = rgb[numpy.isfinite(rgb)]
        return {
            "width": int(spec.width),
            "height": int(spec.height),
            "channels": names,
            "decodedSha256": hashlib.sha256(values.tobytes()).hexdigest(),
            "nonFiniteCount": int(values.size - finite.sum()),
            "rgbDynamicRange": float(finite_rgb.max() - finite_rgb.min()) if finite_rgb.size else 0.0,
            "meanRgb": float(finite_rgb.mean()) if finite_rgb.size else 0.0,
        }
    finally:
        image.close()


def main():
    args = arguments()
    repository = args.repository_root.resolve(strict=True)
    root = args.formal_root.resolve(strict=True)
    loaded = Path(bpy.data.filepath).resolve(strict=True)
    render_report_path = args.render_report.resolve(strict=True)
    output = args.output.resolve()
    require(render_report_path == root / "reports/render-report.json" and output == root / "reports/independent-audit.json", "output contract mismatch")
    require(bpy.app.version_string == "5.2.0 LTS" and bpy.app.build_hash.decode() == "fbe6228777e7", "Blender runtime mismatch")
    require(args.source_sha256 == SCENE_SHA256 and sha256_file(loaded) == SCENE_SHA256, "source scene identity mismatch")
    require(os.environ.get("OCIO", "").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"), "OCIO mismatch")
    render_report = json.loads(render_report_path.read_text(encoding="utf-8"))
    require(valid_self(render_report, "reportHash") and render_report.get("status") == "PASS", "render report invalid")
    require(len(render_report.get("frames", [])) == 288, "render report frame count")
    scene = bpy.context.scene
    require(scene.frame_start == 1 and scene.frame_end == 288 and scene.render.fps == 24, "source timeline mismatch")
    expected_markers = [
        ("SHOT_WIDE_APPROACH", 1, "CAM_WIDE_APPROACH"),
        ("SHOT_MEDIUM_CONTACT", 97, "CAM_MEDIUM_CONTACT"),
        ("SHOT_CLOSE_REFLECTION", 193, "CAM_CLOSE_MOTION_TERMINAL"),
    ]
    markers = sorted((marker.name, int(marker.frame), marker.camera.name if marker.camera else None) for marker in scene.timeline_markers)
    require(sorted(expected_markers) == markers, "source markers mismatch")

    routing = []
    pixels = []
    for frame in range(1, 289):
        scene.frame_set(frame)
        expected_marker, expected_camera = expected_route(frame)
        selected = max((marker for marker in scene.timeline_markers if marker.frame <= frame), key=lambda marker: (marker.frame, marker.name))
        marker = selected.name
        camera = selected.camera.name if selected.camera else None
        routing.append({"frame": frame, "marker": marker, "camera": camera, "expectedMarker": expected_marker, "expectedCamera": expected_camera, "exact": marker == expected_marker and camera == expected_camera})
        row = render_report["frames"][frame - 1]
        require(row.get("frame") == frame and row.get("marker") == expected_marker and row.get("camera") == expected_camera, f"render report routing mismatch {frame}")
        path = repository / row["png"]["uri"]
        require(path.resolve(strict=True) == path and path.parent == root / "frames", f"unsafe frame path {frame}")
        require(sha256_file(path) == row["png"]["sha256"] and path.stat().st_size == row["png"]["bytes"], f"frame identity mismatch {frame}")
        decoded = decode_png(path)
        pixels.append({"frame": frame, "marker": marker, "camera": camera, "fileSha256": row["png"]["sha256"], **decoded})

    close_camera = bpy.data.objects.get("CAM_CLOSE_MOTION_TERMINAL")
    require(close_camera is not None and close_camera.type == "CAMERA", "close camera absent")
    close_geometry = [geometry(scene, frame, close_camera) for frame in range(193, 289)]
    hand = bpy.data.objects.get("HAND_R_SOCKET")
    touch = bpy.data.objects.get("CONSOLE_TOUCH")
    core = bpy.data.objects.get("B62_CORE")
    warm = bpy.data.objects.get("LIGHT_CORE_WARM")
    require(all(item is not None for item in (hand, touch, core, warm)), "causal objects absent")
    causal = []
    for frame in STATE_FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        causal.append({
            "frame": frame,
            "coreActivation": float(core["bfs_core_activation"]),
            "warmEnergy": float(warm.data.energy),
            "contactDistanceM": float((hand.matrix_world.translation - touch.matrix_world.translation).length),
        })

    per_frame_pass = [
        row["width"] == 640 and row["height"] == 360 and row["nonFiniteCount"] == 0
        and row["rgbDynamicRange"] > 1 / 255 and 0.0001 < row["meanRgb"] < 0.9999
        for row in pixels
    ]
    decoded_by_frame = {row["frame"]: row["decodedSha256"] for row in pixels}
    shot_distinct = []
    for start, end, marker, camera in CAMERAS:
        shot_distinct.append({"marker": marker, "camera": camera, "frames": [start, end], "distinctDecodedDigests": len({decoded_by_frame[frame] for frame in range(start, end + 1)})})
    cut_pairs = [{"frames": [left, right], "different": decoded_by_frame[left] != decoded_by_frame[right]} for left, right in ((96, 97), (192, 193))]
    activation = [row["coreActivation"] for row in causal]
    energies = [row["warmEnergy"] for row in causal]
    causal_pass = activation == [0.0, 0.0, 0.5, 1.0, 1.0] and causal[2]["contactDistanceM"] <= 0.02 and energies[0] == energies[1] == 0 and 0 < energies[2] < energies[3] == energies[4]
    outcome = {
        "routingAllExact": all(row["exact"] for row in routing),
        "pixelsAllPass": all(per_frame_pass),
        "shotDistinctAllPass": all(row["distinctDecodedDigests"] >= 2 for row in shot_distinct),
        "wholeDistinctDecodedDigests": len(set(decoded_by_frame.values())),
        "wholeDistinctPass": len(set(decoded_by_frame.values())) >= 10,
        "cutPairsAllDiffer": all(row["different"] for row in cut_pairs),
        "closeGeometryAllPass": all(row["feasible"] for row in close_geometry),
        "causalStatePass": causal_pass,
    }
    document = write_hashed(output, {
        "schemaVersion": "bfs.b62TerminalAnimaticIndependentAudit.v0.1",
        "experimentId": EXPERIMENT_ID,
        "status": "PASS",
        "source": {"uri": loaded.relative_to(repository).as_posix(), "sha256": sha256_file(loaded)},
        "renderReport": {"uri": render_report_path.relative_to(repository).as_posix(), "sha256": sha256_file(render_report_path), "reportHash": render_report["reportHash"]},
        "routing": routing,
        "pixels": pixels,
        "shotDistinct": shot_distinct,
        "cutPairs": cut_pairs,
        "closeGeometry": close_geometry,
        "causalState": causal,
        "outcome": outcome,
        "decoder": {"openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__, "dtype": "little-endian-float32-RGBA"},
        "blender": {"version": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode()},
        "operations": {"blenderStarts": 1, "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    })
    print(f"BFS_B62_T2_INDEPENDENT PASS geometry={outcome['closeGeometryAllPass']} pixels={outcome['pixelsAllPass']} {document['reportHash']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B62_T2_INDEPENDENT_ERROR {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
