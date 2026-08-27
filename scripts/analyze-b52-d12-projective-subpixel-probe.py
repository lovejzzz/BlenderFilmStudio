#!/usr/bin/env python3
"""Development-only analysis for the B52-D12 projective subpixel probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_parts(path: Path) -> dict[str, np.ndarray]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    parts: dict[str, np.ndarray] = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return parts


def bilinear(image: np.ndarray, qx: np.ndarray, qy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width, _ = image.shape
    x0 = np.floor(qx).astype(np.int64)
    y0 = np.floor(qy).astype(np.int64)
    valid = (x0 >= 0) & (y0 >= 0) & (x0 + 1 < width) & (y0 + 1 < height)
    x0c = np.clip(x0, 0, width - 1)
    y0c = np.clip(y0, 0, height - 1)
    x1c = np.clip(x0 + 1, 0, width - 1)
    y1c = np.clip(y0 + 1, 0, height - 1)
    fx = (qx - x0).astype(np.float64)
    fy = (qy - y0).astype(np.float64)
    a = image[y0c, x0c].astype(np.float64)
    b = image[y0c, x1c].astype(np.float64)
    c = image[y1c, x0c].astype(np.float64)
    d = image[y1c, x1c].astype(np.float64)
    result = (
        a * ((1.0 - fx) * (1.0 - fy))[..., None]
        + b * (fx * (1.0 - fy))[..., None]
        + c * ((1.0 - fx) * fy)[..., None]
        + d * (fx * fy)[..., None]
    ).astype("<f4")
    return result, valid


def nearest(image: np.ndarray, qx: np.ndarray, qy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    height, width, _ = image.shape
    xi = np.rint(qx).astype(np.int64)
    yi = np.rint(qy).astype(np.int64)
    valid = (xi >= 0) & (yi >= 0) & (xi < width) & (yi < height)
    return image[np.clip(yi, 0, height - 1), np.clip(xi, 0, width - 1)].copy(), valid


def metrics(reconstructed: np.ndarray, current: np.ndarray, mask: np.ndarray) -> dict:
    error = reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64)
    values = np.abs(error[mask])
    signed = error[mask]
    mse = float(np.mean(np.square(signed)))
    return {
        "samplePixels": int(np.count_nonzero(mask)),
        "maximum": float(np.max(values)),
        "p99": float(np.quantile(values, 0.99)),
        "rmse": math.sqrt(mse),
        "mae": float(np.mean(values)),
        "signedMeanRgb": [float(np.mean(signed[:, channel])) for channel in range(3)],
        "psnrUnitRange": float("inf") if mse == 0.0 else -10.0 * math.log10(mse),
    }


def analytic_vector(width: int, height: int) -> np.ndarray:
    """Independent pinhole/ray-plane oracle for the development trajectory."""
    lens = 50.0
    sensor_width = 36.0
    camera_z = 10.0
    previous_location = np.asarray((-0.040, 0.030, 0.000), dtype=np.float64)
    current_location = np.asarray((0.015, -0.025, 0.180), dtype=np.float64)
    yy, xx = np.mgrid[0:height, 0:width]
    u = (xx.astype(np.float64) + 0.5) / width
    v_bottom = 1.0 - (yy.astype(np.float64) + 0.5) / height
    ray_x = (u - 0.5) * sensor_width / lens
    ray_y = (v_bottom - 0.5) * sensor_width * (height / width) / lens
    ray_z = -np.ones_like(ray_x)
    distance = (current_location[2] - camera_z) / ray_z
    current_world_x = ray_x * distance
    current_world_y = ray_y * distance
    local_x = current_world_x - current_location[0]
    local_y = current_world_y - current_location[1]
    previous_world_x = local_x + previous_location[0]
    previous_world_y = local_y + previous_location[1]
    previous_depth = camera_z - previous_location[2]
    previous_u = 0.5 + (previous_world_x / previous_depth) * lens / sensor_width
    previous_v_bottom = 0.5 + (previous_world_y / previous_depth) * lens / (sensor_width * height / width)
    previous_x = previous_u * width - 0.5
    previous_y_top = (1.0 - previous_v_bottom) * height - 0.5
    expected = np.empty((height, width, 2), dtype=np.float64)
    expected[..., 0] = previous_x - xx
    expected[..., 1] = yy - previous_y_top
    return expected


def main() -> None:
    args = arguments()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D12 development analysis")
    previous = load_parts(args.input_dir / "frame-0.exr")
    current = load_parts(args.input_dir / "frame-1.exr")
    layer = "BFS_D12_DEV_LAYER"
    previous_rgba = previous[f"{layer}.Combined"]
    current_rgba = current[f"{layer}.Combined"]
    vector = current[f"{layer}.Vector"]
    height, width, _ = current_rgba.shape
    yy, xx = np.mgrid[0:height, 0:width]

    # Blender Vector.XY is previous-screen minus current-screen. OIIO arrays
    # use a top-left origin, so the vertical component changes sign.
    qx = xx.astype(np.float64) + vector[..., 0].astype(np.float64)
    qy = yy.astype(np.float64) - vector[..., 1].astype(np.float64)
    wrong_qx = xx.astype(np.float64) - vector[..., 0].astype(np.float64)
    wrong_qy = yy.astype(np.float64) + vector[..., 1].astype(np.float64)
    bilinear_image, bilinear_bounds = bilinear(previous_rgba, qx, qy)
    wrong_image, wrong_bounds = bilinear(previous_rgba, wrong_qx, wrong_qy)
    nearest_image, nearest_bounds = nearest(previous_rgba, qx, qy)

    previous_depth = previous[f"{layer}.Depth"]
    current_depth = current[f"{layer}.Depth"]
    sampled_previous_depth, depth_bounds = bilinear(previous_depth, qx, qy)

    owner = current[f"{layer}.Object Index"][..., 0]
    base_mask = (owner == np.float32(8120.0)) & (current_rgba[..., 3] > 0.999) & (previous_rgba[..., 3] > 0.999)
    margin = (xx >= 3) & (xx < width - 3) & (yy >= 3) & (yy < height - 3)
    mask = base_mask & margin & bilinear_bounds & wrong_bounds & nearest_bounds & depth_bounds
    fractional_distance = np.abs(vector[..., :2].astype(np.float64) - np.rint(vector[..., :2].astype(np.float64)))
    moving = base_mask & (np.linalg.norm(vector[..., :2].astype(np.float64), axis=2) > 1e-6)
    expected_vector = analytic_vector(width, height)
    endpoint_error = vector[..., :2].astype(np.float64) - expected_vector
    endpoint_values = np.abs(endpoint_error[moving])

    report = {
        "schemaVersion": "bfs.projectiveSubpixelDevelopmentAnalysis.v0.1",
        "status": "DEVELOPMENT_ONLY",
        "pid": os.getpid(),
        "resolution": [width, height],
        "vector": {
            "movingPixels": int(np.count_nonzero(moving)),
            "xyMinimum": [float(np.min(vector[..., c][moving])) for c in range(2)],
            "xyMaximum": [float(np.max(vector[..., c][moving])) for c in range(2)],
            "fractionalDistanceMaximum": float(np.max(fractional_distance[moving])),
            "fractionalDistanceP50": float(np.quantile(fractional_distance[moving], 0.5)),
            "fractionalComponentsBeyond1Over1024": int(np.count_nonzero(fractional_distance[moving] > 1.0 / 1024.0)),
            "analyticEndpointMaximum": float(np.max(endpoint_values)),
            "analyticEndpointP99": float(np.quantile(endpoint_values, 0.99)),
            "analyticEndpointRmse": float(np.sqrt(np.mean(np.square(endpoint_error[moving])))),
        },
        "formula": {"qx": "x + Vector.X", "qyTopLeft": "y - Vector.Y", "kernel": "bilinear clip"},
        "metrics": {
            "correctBilinear": metrics(bilinear_image, current_rgba, mask),
            "wrongSignBilinear": metrics(wrong_image, current_rgba, mask),
            "correctNearest": metrics(nearest_image, current_rgba, mask),
        },
        "depthIdentityCounterexample": {
            "maximumAbsoluteDelta": float(np.max(np.abs(sampled_previous_depth[..., 0][mask] - current_depth[..., 0][mask]))),
            "minimumAbsoluteDelta": float(np.min(np.abs(sampled_previous_depth[..., 0][mask] - current_depth[..., 0][mask]))),
            "d9StyleToleranceMaximum": float(np.max(np.maximum(1.0, current_depth[..., 0][mask]) / 1024.0)),
            "pixelsRejectedByDirectDepthEquality": int(
                np.count_nonzero(
                    np.abs(sampled_previous_depth[..., 0][mask] - current_depth[..., 0][mask])
                    > np.maximum(1.0, current_depth[..., 0][mask]) / 1024.0
                )
            ),
            "evaluatedPixels": int(np.count_nonzero(mask)),
        },
        "diagnosticHashes": {
            "correctBilinearRgba32": sha256_bytes(np.ascontiguousarray(bilinear_image, dtype="<f4").tobytes()),
            "wrongSignBilinearRgba32": sha256_bytes(np.ascontiguousarray(wrong_image, dtype="<f4").tobytes()),
            "correctNearestRgba32": sha256_bytes(np.ascontiguousarray(nearest_image, dtype="<f4").tobytes()),
            "maskU8": sha256_bytes(np.ascontiguousarray(mask, dtype=np.uint8).tobytes()),
        },
        "nonClaims": ["not preregistered", "not fresh holdout", "not a scientific verdict"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(report["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()
