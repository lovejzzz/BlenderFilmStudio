#!/usr/bin/env python3
"""Independently reopen B61 EXRs in Blender and recompute decoded Combined digests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import bpy
import numpy
import OpenImageIO as oiio


EXPECTED_OIIO_VERSION = "3.1.13.1"
EXPECTED_NUMPY_VERSION = "2.3.4"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def normalize_canonical_numbers(value: object) -> object:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize_canonical_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_canonical_numbers(item) for key, item in value.items()}
    return value


def canonical(value: object) -> bytes:
    normalized = normalize_canonical_numbers(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_self_hash(record: dict, field: str) -> bool:
    body = dict(record)
    observed = body.pop(field, None)
    return observed == sha256_bytes(canonical(body))


def write_hashed(path: Path, body: dict, hash_field: str) -> dict:
    record = {**body, hash_field: sha256_bytes(canonical(body))}
    with path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def decoded_digest(path: Path) -> dict:
    if oiio.VERSION_STRING != EXPECTED_OIIO_VERSION or numpy.__version__ != EXPECTED_NUMPY_VERSION:
        raise RuntimeError("Bundled OpenImageIO/NumPy version mismatch")
    image_input = oiio.ImageInput.open(str(path))
    if image_input is None:
        raise RuntimeError("OpenImageIO could not open multilayer EXR")
    try:
        candidates = []
        subimage = 0
        while image_input.seek_subimage(subimage, 0):
            spec = image_input.spec()
            names = list(spec.channelnames)
            positions = {name: index for index, name in enumerate(names)}
            for name in names:
                if not name.endswith(".R"):
                    continue
                prefix = name[:-2]
                if prefix.split(".")[-1] != "Combined":
                    continue
                wanted = [f"{prefix}.{component}" for component in "RGBA"]
                if all(channel in positions for channel in wanted):
                    candidates.append((subimage, spec.width, spec.height, spec.nchannels, prefix, wanted, [positions[channel] for channel in wanted]))
            subimage += 1
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one Combined RGBA quartet, found {len(candidates)}")
        subimage, width, height, channel_count, prefix, names, indices = candidates[0]
        pixels = image_input.read_image(subimage, 0, 0, channel_count, oiio.FLOAT)
        if pixels is None:
            raise RuntimeError(f"OpenImageIO read_image failed: {image_input.geterror()}")
        array_value = numpy.asarray(pixels)
        if tuple(array_value.shape) != (height, width, channel_count):
            raise RuntimeError(f"Decoded shape mismatch: {array_value.shape}")
        values = numpy.ascontiguousarray(array_value[..., indices], dtype=numpy.dtype("<f4"))
        non_finite = int(values.size - numpy.isfinite(values).sum())
        return {
            "projection": "DECODED_COMBINED_RGBA_FLOAT32_LE",
            "decoder": {"module": "OpenImageIO", "version": oiio.VERSION_STRING, "numpyVersion": numpy.__version__, "subimage": subimage, "prefix": prefix, "channelNames": names, "channelIndices": indices},
            "width": width,
            "height": height,
            "channels": 4,
            "floatCount": int(values.size),
            "sha256": sha256_bytes(values.tobytes(order="C")),
            "nonFiniteCount": non_finite,
        }
    finally:
        image_input.close()


def main() -> None:
    args = parse_args()
    root = args.repository_root.resolve(strict=True)
    contract_path = args.contract.resolve(strict=True)
    formal_root = args.formal_root.resolve(strict=True)
    output = args.output.resolve(strict=False)
    for candidate, label in [(contract_path, "contract"), (formal_root, "formal root"), (output.parent, "output parent")]:
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise RuntimeError(f"{label} is outside repository root") from error
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    ocio = contract["runtime"]["ocio"]
    expected_ocio = (root / ocio["uri"]).resolve(strict=True)
    if os.environ.get("OCIO") != str(expected_ocio):
        raise RuntimeError("Independent audit OCIO environment mismatch")

    rows = []
    for shot in contract["shots"]:
        for repetition in contract["render"]["repetitions"]:
            run_dir = formal_root / "runs" / f"{shot['label']}-{repetition}"
            for frame in contract["render"]["frames"]:
                report_path = run_dir / f"frame-{frame:04d}.pixel.json"
                exr_path = run_dir / f"frame-{frame:04d}.exr"
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if not valid_self_hash(report, "reportHash"):
                    raise RuntimeError(f"Pixel report self-hash mismatch: {report_path}")
                observed = decoded_digest(exr_path)
                if observed["sha256"] != report["decodedCombined"]["sha256"] or observed["nonFiniteCount"] != 0:
                    raise RuntimeError(f"Independent decoded pixel mismatch: {shot['label']}-{repetition}-{frame}")
                rows.append({
                    "shot": shot["label"],
                    "repetition": repetition,
                    "frame": frame,
                    "pixelSha256": observed["sha256"],
                    "width": observed["width"],
                    "height": observed["height"],
                    "decoder": observed["decoder"],
                    "reportHash": report["reportHash"],
                })
    record = write_hashed(output, {
        "schemaVersion": "bfs.cinematicRenderExrReopenAudit.v0.1",
        "status": "PASS",
        "rows": rows,
        "operations": {"blenderProcesses": 1, "exrFilesOpened": len(rows), "renderCalls": 0, "modelCalls": 0, "networkCalls": 0, "dockerProcesses": 0},
    }, "auditHash")
    print(f"BFS_B61_EXR_AUDIT_OK rows={len(rows)} {record['auditHash']}")


if __name__ == "__main__":
    main()
