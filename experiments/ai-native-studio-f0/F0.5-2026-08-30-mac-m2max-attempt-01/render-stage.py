# SPDX-License-Identifier: GPL-2.0-or-later
"""Frozen F0.5 headless renderer for one approved B01 preview/final job."""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy


EXPECTED_SOURCE_SHA = "648ba4e5c0be2620f0da85dd8fdc0a23d878c39054e61e69029221b5457da942"
EXPECTED_JOB_HASH = "41a16a9c77896b44203bd2d53961be96df4681b2e95f97312778c11fd7ed254c"
EXPECTED_OCIO_SHA = "24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15"
EXPECTED_PLAN_HASH = "316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf"
EXPECTED_STRUCTURE_HASH = "e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8"
EXPECTED_BUILD_HASH = "b47eae224b6d"


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest(path):
    return sha_bytes(path.read_bytes())


def verify_self_hash(path, field):
    value = json.loads(path.read_text())
    expected = value.pop(field)
    actual = sha_bytes((json.dumps(value, indent=2) + "\n").encode())
    if actual != expected:
        raise RuntimeError(f"{path.name} self hash mismatch")
    return expected


def exclusive_json(path, body, hash_field):
    pretty = json.dumps(body, indent=2) + "\n"
    record = {**body, hash_field: sha_bytes(pretty.encode())}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(record, indent=2) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return record


parser = argparse.ArgumentParser()
parser.add_argument("--repository-root", type=Path, required=True)
parser.add_argument("--evidence-root", type=Path, required=True)
parser.add_argument("--stage", choices=("preview", "final"), required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
parser.add_argument("--pause-before-render", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
repository = args.repository_root.resolve(strict=True)
evidence = (repository / args.evidence_root).resolve(strict=True)
source = repository / "experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-03/b01/artifacts/scene.blend"
job = evidence / "job-manifest.json"
output = (repository / args.output).resolve()
report = (repository / args.report).resolve()
for target in (output, report):
    if evidence != target and evidence not in target.parents:
        raise RuntimeError("Output escaped immutable evidence root")
    if target.exists():
        raise RuntimeError(f"Formal target already exists: {target}")
if digest(source) != EXPECTED_SOURCE_SHA:
    raise RuntimeError("Source blend identity mismatch")
if verify_self_hash(job, "manifestHash") != EXPECTED_JOB_HASH:
    raise RuntimeError("Job manifest identity mismatch")
if "--enable-autoexec" in sys.argv or bpy.context.preferences.filepaths.use_scripts_auto_execute:
    raise RuntimeError("Auto-execute scripts must remain disabled")

bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
scene = bpy.context.scene
if scene.get("bfs_plan_hash") != EXPECTED_PLAN_HASH:
    raise RuntimeError("Plan identity mismatch")
if scene.get("bfs_structure_hash") != EXPECTED_STRUCTURE_HASH:
    raise RuntimeError("Semantic structure identity mismatch")
if scene.get("bfs_product_build_hash") != EXPECTED_BUILD_HASH:
    raise RuntimeError("Product provenance mismatch")
if scene.get("bfs_ocio_sha256") != EXPECTED_OCIO_SHA:
    raise RuntimeError("OCIO identity mismatch")
if scene.frame_start != 1 or scene.camera is None:
    raise RuntimeError("Frozen frame/camera state mismatch")

scene.frame_set(1)
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.use_file_extension = True
scene.render.film_transparent = False
scene.render.filepath = str(output)
scene.render.image_settings.color_mode = "RGBA"
render_contract = None
if args.stage == "preview":
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    render_contract = {
        "engine": scene.render.engine,
        "frame": 1,
        "resolution": [640, 360, 100],
        "samples": scene.eevee.taa_render_samples,
        "fileFormat": scene.render.image_settings.file_format,
        "colorMode": scene.render.image_settings.color_mode,
        "colorDepth": scene.render.image_settings.color_depth,
    }
else:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.seed = 24082601
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_depth = "16"
    scene.render.image_settings.exr_codec = "ZIP"
    view_layer = bpy.context.view_layer
    view_layer.use_pass_z = True
    view_layer.use_pass_normal = True
    render_contract = {
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "frame": 1,
        "resolution": [640, 360, 100],
        "samples": scene.cycles.samples,
        "seed": scene.cycles.seed,
        "animatedSeed": scene.cycles.use_animated_seed,
        "denoising": scene.cycles.use_denoising,
        "threadsMode": scene.render.threads_mode,
        "threads": scene.render.threads,
        "fileFormat": scene.render.image_settings.file_format,
        "colorDepth": scene.render.image_settings.color_depth,
        "exrCodec": scene.render.image_settings.exr_codec,
        "passes": {"depth": view_layer.use_pass_z, "normal": view_layer.use_pass_normal},
    }

if args.pause_before_render:
    print(f"F05_READY_FOR_CONTROLLED_INTERRUPT stage={args.stage} renderCalls=0 outputAbsent={not output.exists()}", flush=True)
    time.sleep(120)
    raise RuntimeError("Controlled interrupt was not delivered")

started = time.perf_counter()
result = bpy.ops.render.render(write_still=True)
render_seconds = time.perf_counter() - started
if "FINISHED" not in result:
    raise RuntimeError(f"Render failed: {sorted(result)}")
if not output.is_file():
    raise RuntimeError("Render output missing")
if digest(source) != EXPECTED_SOURCE_SHA:
    raise RuntimeError("Source blend changed during render")
if not math.isfinite(render_seconds) or render_seconds <= 0:
    raise RuntimeError("Invalid render duration")

body = {
    "schemaVersion": "bfs.f0.5.productStageReport.v0.1",
    "jobId": "F05-B01-RENDER-001",
    "stage": args.stage.upper(),
    "status": "PASS",
    "renderCalls": 1,
    "mouseInteractions": 0,
    "renderSeconds": render_seconds,
    "source": {
        "blendSha256BeforeAndAfter": EXPECTED_SOURCE_SHA,
        "planHash": EXPECTED_PLAN_HASH,
        "semanticStructureSha256": EXPECTED_STRUCTURE_HASH,
        "productBuildHash": EXPECTED_BUILD_HASH,
        "ocioConfigSha256": EXPECTED_OCIO_SHA,
    },
    "renderContract": render_contract,
    "output": {"uri": str(output.relative_to(evidence)), "bytes": output.stat().st_size, "sha256": digest(output)},
}
exclusive_json(report, body, "stageReportHash")
print(f"F05_STAGE_PASS stage={args.stage.upper()} renders=1 bytes={output.stat().st_size} sha256={digest(output)}", flush=True)
