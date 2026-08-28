#!/usr/bin/env python3
"""Analyze the frozen D12.14-P1 Position-oracle development probe."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "2ccffbcfe861fd80406901b417cf4cd2b2b8977c6925d6fb73e3d0328092efe3"
H1_SPEC_SHA256 = "7ff239d91dca6ea8708ce4cac955dd0b129ae067028a77ec1699a43a236195a8"
H1_CONSUMER_SHA256 = "7bae8c665df9d904369fe7774204c42024a2b15c3a4b615bd7e8d28ab8238c40"
FIXTURE_ID = "RIGID_NEITHER_FRESH_197X139"
LAYER = "BFS_D1214P1_MASTER"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_h1(root: Path):
    path = root / "scripts/reconstruct-b52-d12-14-h1-rigid-directional.py"
    if sha_file(path) != H1_CONSUMER_SHA256:
        raise RuntimeError("P1 analyzer H1 consumer identity mismatch")
    module_spec = importlib.util.spec_from_file_location("bfs_d1214_h1_consumer_for_p1", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("P1 analyzer cannot load H1 consumer")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list)):
        return [json_value(row) for row in value]
    return str(value)


def load_exr(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    parts = {}
    channels = {}
    formats = {}
    metadata = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        channels[name] = list(spec.channelnames)
        formats[name] = str(spec.format)
        metadata[name] = {row.name: json_value(row.value) for row in spec.extra_attribs}
    return {"parts": parts, "channels": channels, "formats": formats, "metadata": metadata}


def percentile_summary(values: np.ndarray) -> dict:
    finite = np.asarray(values, dtype=np.float64)
    if finite.size == 0 or not np.isfinite(finite).all():
        raise RuntimeError("P1 non-finite or empty metric")
    return {
        "minimum": float(np.min(finite)),
        "p50": float(np.quantile(finite, 0.50)),
        "p90": float(np.quantile(finite, 0.90)),
        "p99": float(np.quantile(finite, 0.99)),
        "maximum": float(np.max(finite)),
    }


def metadata_differences(left: dict, right: dict) -> list[dict]:
    rows = []
    for part in sorted(set(left) | set(right)):
        lrow, rrow = left.get(part, {}), right.get(part, {})
        for name in sorted(set(lrow) | set(rrow)):
            if lrow.get(name) != rrow.get(name):
                rows.append({"subimage": part, "name": name, "repeat1": lrow.get(name), "repeat2": rrow.get(name)})
    return rows


def main() -> None:
    cli = arguments()
    repo = Path(__file__).resolve().parents[1]
    if sha_file(cli.spec) != SPEC_SHA256 or cli.output.exists():
        raise RuntimeError("P1 analyzer spec identity or fresh output violation")
    spec = json.loads(cli.spec.read_text())
    h1_spec_path = repo / spec["parents"]["h1Spec"]["uri"]
    if sha_file(h1_spec_path) != H1_SPEC_SHA256:
        raise RuntimeError("P1 analyzer H1 spec identity mismatch")
    h1_spec = json.loads(h1_spec_path.read_text())
    h1 = load_h1(repo)
    fixture = h1.effective_fixture(h1_spec, next(row for row in h1_spec["fixtures"] if row["id"] == FIXTURE_ID))
    width, height = fixture["resolution"]

    expected_channels = {
        f"{LAYER}.Combined": [f"{LAYER}.Combined.{name}" for name in ("R", "G", "B", "A")],
        f"{LAYER}.Depth": [f"{LAYER}.Depth.Z"],
        f"{LAYER}.Position": [f"{LAYER}.Position.{name}" for name in ("X", "Y", "Z")],
        f"{LAYER}.Vector": [f"{LAYER}.Vector.{name}" for name in ("X", "Y", "Z", "W")],
        f"{LAYER}.Object Index": [f"{LAYER}.Object Index.X"],
        f"{LAYER}.Material Index": [f"{LAYER}.Material Index.X"],
    }
    expected_roster = list(expected_channels)
    loaded = {}
    source_rows = []
    for repeat in (1, 2):
        source_dir = cli.root / "sources" / f"R{repeat}"
        report_path = source_dir / "frame-1-report.json"
        exr_path = source_dir / "frame-1.exr"
        report = json.loads(report_path.read_text())
        report_body = {key: value for key, value in report.items() if key != "reportHash"}
        if report.get("reportHash") != canonical_hash(report_body):
            raise RuntimeError(f"P1 source report self-hash mismatch R{repeat}")
        if report.get("experimentId") != spec["experimentId"] or report.get("specSha256") != SPEC_SHA256 or report.get("repeat") != repeat:
            raise RuntimeError(f"P1 source identity mismatch R{repeat}")
        if report.get("output", {}).get("sha256") != sha_file(exr_path):
            raise RuntimeError(f"P1 source EXR binding mismatch R{repeat}")
        if report.get("passState", {}).get("Position") is not True or report.get("passState", {}).get("viewLayer") != LAYER:
            raise RuntimeError(f"P1 Position pass state mismatch R{repeat}")
        loaded[repeat] = load_exr(exr_path)
        source_rows.append({
            "repeat": repeat,
            "reportUri": str(report_path.relative_to(repo)),
            "reportSha256": sha_file(report_path),
            "reportHash": report["reportHash"],
            "exrUri": str(exr_path.relative_to(repo)),
            "exrSha256": sha_file(exr_path),
            "exrBytes": exr_path.stat().st_size,
        })

    roster_gate = all(list(loaded[repeat]["parts"]) == expected_roster for repeat in (1, 2))
    channels_gate = all(loaded[repeat]["channels"] == expected_channels for repeat in (1, 2))
    formats_gate = all(all(value == "float" for value in loaded[repeat]["formats"].values()) for repeat in (1, 2))
    shapes_gate = all(
        loaded[repeat]["parts"][part].shape == (height, width, len(expected_channels[part]))
        for repeat in (1, 2)
        for part in expected_roster
    )
    decoded_exact = all(np.array_equal(loaded[1]["parts"][part], loaded[2]["parts"][part]) for part in expected_roster)
    decoded = {
        f"R{repeat}": {
            part: {
                "shape": list(loaded[repeat]["parts"][part].shape),
                "dtype": "<f4",
                "sha256": sha_bytes(loaded[repeat]["parts"][part].tobytes()),
            }
            for part in expected_roster
        }
        for repeat in (1, 2)
    }
    differences = metadata_differences(loaded[1]["metadata"], loaded[2]["metadata"])
    allowed_metadata = set(spec["gates"]["containerMetadataDifferenceAllowlist"])
    metadata_gate = all(row["name"] in allowed_metadata for row in differences)

    arrays = loaded[1]["parts"]
    rgba = arrays[f"{LAYER}.Combined"]
    depth = arrays[f"{LAYER}.Depth"][..., 0]
    position = arrays[f"{LAYER}.Position"]
    vector = arrays[f"{LAYER}.Vector"]
    object_index = arrays[f"{LAYER}.Object Index"][..., 0]
    material_index = arrays[f"{LAYER}.Material Index"][..., 0]
    foreground = fixture["owners"][1]
    mask = (
        (material_index == np.float32(foreground["materialPassIndex"]))
        & (object_index == np.float32(foreground["objectPassIndex"]))
        & (rgba[..., 3] > np.float32(0.999))
    )
    position_count = int(mask.sum())
    position_finite = bool(np.isfinite(position[mask]).all())

    current_owner = h1.transform(foreground["transformByFrame"]["1"])
    previous_owner = h1.transform(foreground["transformByFrame"]["0"])
    current_camera = h1.transform(fixture["cameraByFrame"]["1"])
    previous_camera = h1.transform(fixture["cameraByFrame"]["0"])
    camera_spec = h1_spec["sceneContract"]["camera"]
    lens = float(camera_spec["lensMm"])
    sensor_width = float(camera_spec["sensorWidthMm"])
    vector_error = []
    next_vector = []
    depth_error = []
    center_vector_error = []
    subpixel_x = []
    subpixel_y = []
    for y, x in np.argwhere(mask):
        point = tuple(float(value) for value in position[y, x])
        local = h1.mat_t_vec(current_owner[1], h1.subtract(point, current_owner[0]))
        previous_point = h1.add(previous_owner[0], h1.mat_vec(previous_owner[1], local))
        current_projection = h1.project(point, current_camera, width, height, lens, sensor_width)
        previous_projection = h1.project(previous_point, previous_camera, width, height, lens, sensor_width)
        if current_projection is None or previous_projection is None:
            raise RuntimeError("P1 Position projection left the perspective domain")
        expected = (
            previous_projection[0] - current_projection[0],
            current_projection[1] - previous_projection[1],
        )
        observed = (float(vector[y, x, 0]), float(vector[y, x, 1]))
        vector_error.append(max(abs(observed[index] - expected[index]) for index in range(2)))
        next_vector.append(max(abs(float(vector[y, x, 2])), abs(float(vector[y, x, 3]))))
        depth_error.append(abs(float(depth[y, x]) - current_projection[2]))
        subpixel_x.append(current_projection[0] - float(x))
        subpixel_y.append(current_projection[1] - float(y))
        center = h1.oracle_pixel(h1_spec, fixture, int(x), int(y))
        if center is None:
            raise RuntimeError("P1 pixel-center diagnostic oracle missing")
        center_vector_error.append(max(abs(observed[index] - center["expectedVector"][index]) for index in range(2)))

    vector_error_array = np.asarray(vector_error, dtype=np.float64)
    next_vector_array = np.asarray(next_vector, dtype=np.float64)
    depth_error_array = np.asarray(depth_error, dtype=np.float64)
    tolerance_depth = float(spec["gates"]["currentDepthFromPositionMaximumAbsoluteError"])
    tolerance_vector = float(spec["gates"]["positionOracleVectorMaximumAbsoluteErrorPixels"])
    tolerance_next = float(spec["gates"]["vectorNextMaximumAbsoluteMagnitudePixels"])
    gates = {
        "SOURCE_REPORTS_AND_EXR_BINDINGS": True,
        "EXACT_SUBIMAGE_ROSTER": roster_gate,
        "EXACT_CHANNEL_ROSTER": channels_gate,
        "FLOAT_CHANNEL_FORMATS": formats_gate,
        "EXACT_ARRAY_SHAPES": shapes_gate,
        "FOREGROUND_POSITION_PIXELS": position_count >= int(spec["gates"]["foregroundPositionPixelsMinimum"]),
        "POSITION_FINITE": position_finite,
        "POSITION_TOKENS_EXACT": position_count == width * height,
        "CURRENT_DEPTH_FROM_POSITION": float(depth_error_array.max()) <= tolerance_depth,
        "POSITION_ORACLE_VECTOR": float(vector_error_array.max()) <= tolerance_vector,
        "VECTOR_NEXT_ZERO": float(next_vector_array.max()) <= tolerance_next,
        "DECODED_PASS_REPEAT_IDENTITY": decoded_exact,
        "CONTAINER_METADATA_ALLOWLIST": metadata_gate,
        "OPERATION_BOUNDARY": True,
    }
    passed = all(gates.values())
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalPositionOracleDevelopmentResult.v0.1",
        "experimentId": spec["experimentId"],
        "specSha256": SPEC_SHA256,
        "status": "DEVELOPMENT_COMPLETE",
        "scientificVerdict": None,
        "developmentVerdict": spec["outcomes"]["supported"] if passed else spec["outcomes"]["notSupported"],
        "gates": gates,
        "gatesPassed": sum(gates.values()),
        "gatesTotal": len(gates),
        "source": source_rows,
        "decodedPasses": decoded,
        "repeatIdentity": {
            "decodedArraysExact": decoded_exact,
            "containerBytesExact": source_rows[0]["exrSha256"] == source_rows[1]["exrSha256"],
            "metadataDifferences": differences,
            "differenceNames": sorted({row["name"] for row in differences}),
        },
        "measurements": {
            "foregroundPositionPixels": position_count,
            "positionOracleVectorAbsoluteErrorPixels": percentile_summary(vector_error_array),
            "pixelCenterVectorAbsoluteErrorPixels": percentile_summary(np.asarray(center_vector_error)),
            "currentDepthFromPositionAbsoluteError": percentile_summary(depth_error_array),
            "vectorNextAbsoluteMagnitudePixels": percentile_summary(next_vector_array),
            "currentRasterOffsetFromIntegerPixelX": percentile_summary(np.abs(np.asarray(subpixel_x))),
            "currentRasterOffsetFromIntegerPixelY": percentile_summary(np.abs(np.asarray(subpixel_y))),
        },
        "interpretationBoundary": spec["decisionBoundary"],
        "operationCounts": {
            "blenderProcesses": 2,
            "blenderRenderCalls": 2,
            "cyclesRayRenders": 2,
            "analyzerProcesses": 1,
            "modelCalls": 0,
            "networkCalls": 0,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "pythonExecutableSha256": sha_file(Path(sys.executable)),
            "numpy": np.__version__,
            "openImageIO": oiio.VERSION_STRING,
            "pid": os.getpid(),
        },
    }
    result = {**body, "resultHash": canonical_hash(body)}
    cli.output.parent.mkdir(parents=True, exist_ok=True)
    cli.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D1214P1_ANALYSIS verdict={result['developmentVerdict']} gates={result['gatesPassed']}/{result['gatesTotal']}")


if __name__ == "__main__":
    main()
