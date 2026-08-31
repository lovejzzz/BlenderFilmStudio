#!/usr/bin/env python3
"""Render the preregistered PC.3 integrated slice through a zero-residue EXR-to-PNG adapter."""

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
import OpenImageIO as oiio


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer(): return int(value)
    if isinstance(value, list): return [normalize(item) for item in value]
    if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
    return value
def hash_value(value): return hashlib.sha256(canonical(normalize(value))).hexdigest()
def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def valid_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hash_value(body)
def write_self(path, value, field):
    body = normalize(dict(value)); body[field] = hash_value(body)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try: os.write(descriptor, (json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode()); os.fsync(descriptor)
    finally: os.close(descriptor)
    return body


def decode_combined(path):
    image = oiio.ImageInput.open(str(path))
    if image is None: raise RuntimeError("EXR_OPEN")
    try:
        candidates = []
        subimage = 0
        while image.seek_subimage(subimage, 0):
            spec = image.spec(); names = list(spec.channelnames); positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"): continue
                prefix = name[:-2]; wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted): candidates.append((subimage, spec.width, spec.height, spec.nchannels, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1: raise RuntimeError(f"COMBINED_COUNT_{len(candidates)}")
        subimage, width, height, channels, indices = candidates[0]
        pixels = np.asarray(image.read_image(subimage, 0, 0, channels, oiio.FLOAT), dtype=np.float32).reshape(height, width, channels)
        return np.ascontiguousarray(pixels[..., indices], dtype=np.float32)
    finally: image.close()


def read_rgba(path):
    image = oiio.ImageInput.open(str(path))
    if image is None: raise RuntimeError(f"IMAGE_OPEN_{path}")
    try:
        spec = image.spec(); pixels = np.asarray(image.read_image(format=oiio.FLOAT), dtype=np.float32).reshape(spec.height, spec.width, spec.nchannels)
        if (spec.width, spec.height) != (640, 360): raise RuntimeError("IMAGE_SIZE")
        if pixels.shape[2] == 3: pixels = np.concatenate([pixels, np.ones((360, 640, 1), dtype=np.float32)], axis=2)
        return np.ascontiguousarray(pixels[:, :, :4], dtype=np.float32)
    finally: image.close()


def save_png(path, rgba):
    output_scene = bpy.data.scenes.new("PC3_ISOLATED_PNG_OUTPUT")
    output_scene.display_settings.display_device = "sRGB - Display"
    output_scene.view_settings.view_transform = "ACES 2.0 - SDR 100 nits (Rec.709)"
    output_scene.view_settings.look = "None"
    output_scene.render.image_settings.file_format = "PNG"; output_scene.render.image_settings.color_mode = "RGBA"; output_scene.render.image_settings.color_depth = "8"
    image = bpy.data.images.new("PC3_GENERATED_REVIEW", width=640, height=360, alpha=True, float_buffer=True)
    try:
        image.colorspace_settings.name = "ACEScg"; image.pixels.foreach_set(np.ascontiguousarray(np.flipud(rgba), dtype=np.float32).reshape(-1)); image.update(); image.save_render(filepath=str(path), scene=output_scene)
    finally:
        bpy.data.images.remove(image); bpy.data.scenes.remove(output_scene)


def render_frame(scene, frame, camera, output, scratch):
    scene.frame_set(frame); scene.camera = bpy.data.objects[camera]; scene.render.filepath = str(scratch)
    if output.exists() or scratch.exists(): raise RuntimeError("OUTPUT_EXISTS")
    if "FINISHED" not in bpy.ops.render.render(write_still=True) or not scratch.is_file(): raise RuntimeError("RENDER")
    rgba = decode_combined(scratch)
    if rgba.shape != (360, 640, 4) or not np.isfinite(rgba).all(): raise RuntimeError("PIXELS")
    save_png(output, rgba); scratch.unlink()
    if not output.is_file() or scratch.exists(): raise RuntimeError("ADAPTER")


def write_contact_sheet(spec, evidence):
    rows = []
    for source_root in (Path(spec["baselineA"]["framesRoot"]), evidence / "frames"):
        images = [read_rgba(source_root / f"frame-{frame:04d}.png") for frame in (48, 144, 240)]
        rows.append(np.concatenate(images, axis=1))
    combined = np.concatenate(rows, axis=0)
    path = evidence / "review" / "AB-contact-sheet.png"
    writer = oiio.ImageOutput.create(str(path))
    if writer is None: raise RuntimeError("SHEET_CREATE")
    image_spec = oiio.ImageSpec(combined.shape[1], combined.shape[0], 4, oiio.UINT8)
    if not writer.open(str(path), image_spec): raise RuntimeError("SHEET_OPEN")
    try: writer.write_image((np.clip(combined, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
    finally: writer.close()
    return path


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--evidence-root", type=Path, required=True); parser.add_argument("--work-root", type=Path, required=True); args = parser.parse_args(argv)
spec = json.loads(args.spec.read_text(encoding="utf-8"))
if not valid_self(spec, "specHash") or spec["status"] != "PREREGISTERED_BEFORE_PC3_RENDER": raise RuntimeError("SPEC")
scene = bpy.context.scene; source = Path(bpy.data.filepath); source_before = sha256_file(source)
if source_before != spec["source"]["sha256"]: raise RuntimeError("SOURCE")
scene.render.engine = spec["renderProfile"]["engine"]; scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = spec["renderProfile"]["resolution"]
if scene.render.image_settings.file_format != "OPEN_EXR_MULTILAYER" or scene.render.image_settings.media_type != "MULTI_LAYER_IMAGE": raise RuntimeError("PRODUCTION_OUTPUT_CONTRACT")
scene.eevee.taa_samples = spec["renderProfile"]["samples"]; scene.eevee.taa_render_samples = spec["renderProfile"]["samples"]
scratch = args.work_root / "tmp" / "pc3-current-frame.exr"; records = []
for frame in range(1, 289):
    camera = "CAM_WIDE_APPROACH" if frame <= 96 else "CAM_MEDIUM_CONTACT" if frame <= 192 else "CAM_CLOSE_MOTION_TERMINAL"
    output = args.evidence_root / "frames" / f"frame-{frame:04d}.png"
    render_frame(scene, frame, camera, output, scratch)
    records.append({"frame": frame, "camera": camera, "uri": output.as_posix(), "sha256": sha256_file(output), "bytes": output.stat().st_size})
sheet = write_contact_sheet(spec, args.evidence_root)
if sha256_file(source) != source_before: raise RuntimeError("SOURCE_DRIFT")
record = write_self(args.evidence_root / "render.json", {"schemaVersion": "bfs.pc3Render.v0.1", "status": "PASS", "source": {"path": str(source), "beforeSha256": source_before, "afterSha256": sha256_file(source)}, "frames": records, "contactSheet": {"uri": sheet.as_posix(), "sha256": sha256_file(sheet), "bytes": sheet.stat().st_size}, "outputAdapter": {"temporaryExrWrites": 288, "temporaryExrRetained": 0, "oiioVersion": oiio.VERSION_STRING, "numpyVersion": np.__version__}, "operations": {"BlenderStarts": 1, "renderCalls": 288, "sceneSaves": 0, "networkCalls": 0, "modelCalls": 0, "mouseInteractions": 0}}, "renderHash")
print("PC3_RENDER=" + json.dumps({"status": record["status"], "renderHash": record["renderHash"]}, sort_keys=True), flush=True)
