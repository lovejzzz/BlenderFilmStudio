#!/usr/bin/env python3
"""Fresh-Blender audit of the 288 accepted B62 Cycles EXR frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

import bpy
import numpy
import OpenImageIO as oiio


EXPECTED_BLENDER = "5.2.0 LTS"
EXPECTED_BUILD = "fbe6228777e7"
EXPECTED_OIIO = "3.1.13.1"
EXPECTED_NUMPY = "2.3.4"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def normalize(value):
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, float) and math.isfinite(value):
        return {"$f64be": struct.pack(">d", value).hex()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def canonical(value):
    return json.dumps(normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def valid_self_hash(value, field):
    body = dict(value)
    observed = body.pop(field, None)
    return observed == hashlib.sha256(canonical(body)).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_hashed(path, body, field):
    require(not path.exists(), f"authoritative path exists {path}")
    record = {**body, field: hashlib.sha256(canonical(body)).hexdigest()}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)
    return record


def contained(root, spelling):
    require(isinstance(spelling, str) and spelling and not Path(spelling).is_absolute(), "path must be repository-relative")
    path = (root / spelling).resolve(strict=True)
    path.relative_to(root)
    require(not path.is_symlink(), f"symlink forbidden {spelling}")
    return path


def decode_combined(path):
    image = oiio.ImageInput.open(str(path))
    require(image is not None, f"OpenImageIO open failed {path}")
    try:
        candidates = []
        subimage = 0
        while image.seek_subimage(subimage, 0):
            spec = image.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"):
                    continue
                prefix = name[:-2]
                wanted = [f"{prefix}.{channel}" for channel in "RGBA"]
                if prefix.split(".")[-1] == "Combined" and all(channel in positions for channel in wanted):
                    candidates.append((subimage, spec.width, spec.height, spec.nchannels, prefix, wanted, [positions[channel] for channel in wanted]))
            subimage += 1
        require(len(candidates) == 1, f"expected one Combined RGBA quartet in {path}, found {len(candidates)}")
        subimage, width, height, channel_count, prefix, names, indices = candidates[0]
        pixels = image.read_image(subimage, 0, 0, channel_count, oiio.FLOAT)
        require(pixels is not None, f"OpenImageIO read failed {path}: {image.geterror()}")
        source = numpy.asarray(pixels)
        require(tuple(source.shape) == (height, width, channel_count), f"decoded shape mismatch {path}: {source.shape}")
        rgba = numpy.ascontiguousarray(source[..., indices], dtype=numpy.dtype("<f4"))
        non_finite = int(rgba.size - int(numpy.count_nonzero(numpy.isfinite(rgba))))
        rgb = rgba[..., :3]
        return {
            "subimage": subimage,
            "prefix": prefix,
            "channelNames": names,
            "channelIndices": indices,
            "width": width,
            "height": height,
            "floatCount": int(rgba.size),
            "nonFiniteCount": non_finite,
            "rgbDynamicRange": float(numpy.max(rgb) - numpy.min(rgb)),
            "meanRgb": float(numpy.mean(rgb, dtype=numpy.float64)),
            "decodedCombinedSha256": hashlib.sha256(rgba.tobytes(order="C")).hexdigest(),
        }
    finally:
        image.close()


def main():
    args = arguments()
    root = args.repository_root.resolve(strict=True)
    manifest_path = args.manifest.resolve(strict=True)
    output = args.output.resolve()
    manifest_path.relative_to(root)
    output.parent.resolve(strict=True).relative_to(root)
    require(not output.exists(), "audit output exists")
    require(bpy.app.version_string == EXPECTED_BLENDER and bpy.app.build_hash.decode("ascii") == EXPECTED_BUILD, "Blender runtime mismatch")
    require(oiio.VERSION_STRING == EXPECTED_OIIO and numpy.__version__ == EXPECTED_NUMPY, "decoder runtime mismatch")
    require(os.environ.get("OCIO", "").endswith("color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"), "OCIO binding mismatch")

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest.get("schemaVersion") == "bfs.b62TerminalAcceptedFrameManifest.v0.1", "manifest schema mismatch")
    require(valid_self_hash(manifest, "manifestHash"), "manifest self-hash mismatch")
    require(len(manifest.get("frames", [])) == 288, "manifest must contain 288 frames")

    rows = []
    for expected_frame, binding in enumerate(manifest["frames"], start=1):
        require(binding.get("frame") == expected_frame, f"non-contiguous frame {expected_frame}")
        report_path = contained(root, binding["report"]["uri"])
        exr_path = contained(root, binding["exr"]["uri"])
        require(sha256_file(report_path) == binding["report"]["sha256"], f"report file mismatch frame {expected_frame}")
        require(sha256_file(exr_path) == binding["exr"]["sha256"], f"EXR file mismatch frame {expected_frame}")
        report = json.loads(report_path.read_bytes())
        require(valid_self_hash(report, "reportHash") and report["reportHash"] == binding["report"]["reportHash"], f"report self-hash mismatch frame {expected_frame}")
        observed = decode_combined(exr_path)
        require(observed["width"] == 1920 and observed["height"] == 1080, f"dimensions mismatch frame {expected_frame}")
        require(observed["nonFiniteCount"] == 0 and observed["rgbDynamicRange"] > 1e-6 and 0.0001 < observed["meanRgb"] < 0.9999, f"pixel validity mismatch frame {expected_frame}")
        require(observed["decodedCombinedSha256"] == report["decodedCombined"]["decodedCombinedSha256"] == binding["decodedCombinedSha256"], f"decoded digest mismatch frame {expected_frame}")
        rows.append({"frame": expected_frame, "shot": binding["shot"], "reportHash": report["reportHash"], **observed})
        print(f"BFS_T3_EXR_REOPEN frame={expected_frame} digest={observed['decodedCombinedSha256']}", flush=True)

    record = write_hashed(output, {
        "schemaVersion": "bfs.b62TerminalCyclesExrAudit.v0.1",
        "experimentId": "B62-T3-E1",
        "status": "PASS",
        "runtime": {"blender": bpy.app.version_string, "buildHash": bpy.app.build_hash.decode("ascii"), "openImageIO": oiio.VERSION_STRING, "numpy": numpy.__version__},
        "manifest": {"uri": manifest_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(manifest_bytes).hexdigest(), "manifestHash": manifest["manifestHash"]},
        "rows": rows,
        "operations": {"blenderStarts": 1, "exrFilesOpened": 288, "renderCalls": 0, "modelCalls": 0, "videoModelCalls": 0, "networkCalls": 0, "dockerProcesses": 0, "colimaProcesses": 0},
    }, "auditHash")
    print(f"BFS_T3_EXR_AUDIT_PASS rows=288 audit={record['auditHash']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_T3_EXR_AUDIT_ERROR {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error
