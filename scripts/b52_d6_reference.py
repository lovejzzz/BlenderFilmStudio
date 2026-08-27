#!/usr/bin/env python3
"""Independent B52-D6 float32 raster and destination-sampled warp reference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "28d3c0b292b89d5d056d5521aececbfb6d88b70971d2b500fbff69d2498703be"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def array_hash(array: np.ndarray) -> str:
    canonical = np.ascontiguousarray(array, dtype="<f4")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def fixture_by_id(spec: dict, fixture_id: str) -> dict:
    matches = [item for item in spec["fixtures"] if item["id"] == fixture_id]
    if len(matches) != 1:
        raise RuntimeError(f"unknown or duplicate fixture {fixture_id}")
    return matches[0]


def source_array(spec: dict) -> np.ndarray:
    width, height = spec["raster"]["resolution"]
    source = np.zeros((height, width, 4), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            source[y, x] = (
                np.float32(x / 64.0),
                np.float32(y / 64.0),
                np.float32(((3 * x + 5 * y) % 64) / 64.0),
                np.float32(min(1.0, x / 16.0)),
            )
    return source


def displacement_array(spec: dict, fixture_id: str) -> np.ndarray:
    width, height = spec["raster"]["resolution"]
    field = np.zeros((height, width, 2), dtype=np.float32)
    if fixture_id == "ZERO_NEAREST_CLIP":
        return field
    if fixture_id in {"POSITIVE_INTEGER_NEAREST_CLIP", "POSITIVE_INTEGER_NEAREST_EXTEND", "POSITIVE_INTEGER_NEAREST_REPEAT"}:
        field[..., 0], field[..., 1] = np.float32(5.0), np.float32(-3.0)
        return field
    if fixture_id == "NEGATIVE_INTEGER_NEAREST_CLIP":
        field[..., 0], field[..., 1] = np.float32(-7.0), np.float32(4.0)
        return field
    if fixture_id == "SUBPIXEL_BILINEAR_CLIP":
        field[..., 0], field[..., 1] = np.float32(0.5), np.float32(-0.25)
        return field
    if fixture_id == "DESTINATION_STEP_NEAREST_CLIP":
        field[:, width // 2 :, 0] = np.float32(3.0)
        field[: height // 2, :, 1] = np.float32(-2.0)
        field[height // 2 :, :, 1] = np.float32(1.0)
        return field
    raise RuntimeError(f"no displacement formula for {fixture_id}")


def resolve_index(value: int, size: int, extension: str) -> int | None:
    if extension == "Clip":
        return value if 0 <= value < size else None
    if extension == "Extend":
        return min(max(value, 0), size - 1)
    if extension == "Repeat":
        return value % size
    raise RuntimeError(f"unsupported extension {extension}")


def tap(source: np.ndarray, x: int, y: int, extension_x: str, extension_y: str) -> np.ndarray:
    sx = resolve_index(x, source.shape[1], extension_x)
    sy = resolve_index(y, source.shape[0], extension_y)
    if sx is None or sy is None:
        return np.zeros(4, dtype=np.float32)
    return source[sy, sx]


def reference_warp(source: np.ndarray, displacement: np.ndarray, fixture: dict) -> np.ndarray:
    height, width, _ = source.shape
    output = np.zeros_like(source, dtype=np.float32)
    extension_x = fixture["extensionX"]
    extension_y = fixture["extensionY"]
    for y in range(height):
        for x in range(width):
            dx, dy = displacement[y, x]
            u = np.float32(x) - dx
            v = np.float32(y) + dy
            if fixture["interpolation"] == "Nearest":
                if float(u).is_integer() is False or float(v).is_integer() is False:
                    raise RuntimeError("Nearest fixture contains a non-integer source coordinate")
                output[y, x] = tap(source, int(u), int(v), extension_x, extension_y)
                continue
            if fixture["interpolation"] != "Bilinear":
                raise RuntimeError(f"unsupported interpolation {fixture['interpolation']}")
            x0, y0 = int(np.floor(u)), int(np.floor(v))
            fx, fy = np.float32(u - x0), np.float32(v - y0)
            one = np.float32(1.0)
            w00 = np.float32((one - fx) * (one - fy))
            w10 = np.float32(fx * (one - fy))
            w01 = np.float32((one - fx) * fy)
            w11 = np.float32(fx * fy)
            output[y, x] = (
                tap(source, x0, y0, extension_x, extension_y) * w00
                + tap(source, x0 + 1, y0, extension_x, extension_y) * w10
                + tap(source, x0, y0 + 1, extension_x, extension_y) * w01
                + tap(source, x0 + 1, y0 + 1, extension_x, extension_y) * w11
            )
    return output


def read_rgba(path: Path) -> np.ndarray:
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(f"cannot open {path}: {oiio.geterror()}")
    image_spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 4, oiio.FLOAT), dtype=np.float32)
    image.close()
    if image_spec.nchannels < 4:
        raise RuntimeError(f"expected RGBA image, got {image_spec.nchannels} channels")
    return pixels.reshape(image_spec.height, image_spec.width, 4)


def read_png(path: Path) -> np.ndarray:
    image = oiio.ImageInput.open(str(path))
    if image is None:
        raise RuntimeError(f"cannot open PNG {path}: {oiio.geterror()}")
    image_spec = image.spec()
    pixels = np.asarray(image.read_image(0, 0, 0, 3, oiio.UINT8), dtype=np.uint8)
    image.close()
    return pixels.reshape(image_spec.height, image_spec.width, 3)


def write_png(path: Path, pixels: np.ndarray) -> None:
    encoded = np.ascontiguousarray(pixels, dtype=np.uint8)
    image_spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], 3, oiio.UINT8)
    output = oiio.ImageOutput.create(str(path))
    if output is None or not output.open(str(path), image_spec):
        raise RuntimeError(f"cannot create PNG {path}: {oiio.geterror()}")
    if not output.write_image(encoded):
        raise RuntimeError(f"cannot write PNG {path}: {output.geterror()}")
    output.close()

