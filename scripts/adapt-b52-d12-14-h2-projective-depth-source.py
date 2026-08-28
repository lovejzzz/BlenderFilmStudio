#!/usr/bin/env python3
"""Decode one B52-D12.14-H2 multipart pair into isolated decision/control arrays."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b"
CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92"
DECISION_FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousOwner": "previous-owner.f32",
    "currentOwner": "current-owner.f32",
    "vector": "vector.xy32",
}
CONTROL_FILES = {
    "previousPosition": "previous-position.xyz32",
    "currentPosition": "current-position.xyz32",
    "vectorNext": "vector-next.xy32",
    "previousObjectIndex": "previous-object-index.f32",
    "currentObjectIndex": "current-object-index.f32",
}


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
    parser.add_argument("--correction", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--previous-exr", type=Path, required=True)
    parser.add_argument("--current-exr", type=Path, required=True)
    parser.add_argument("--previous-report", type=Path, required=True)
    parser.add_argument("--current-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list)):
        return [json_value(row) for row in value]
    return str(value)


def expected_channels(layer: str) -> dict[str, list[str]]:
    return {
        f"{layer}.Combined": [f"{layer}.Combined.{channel}" for channel in ("R", "G", "B", "A")],
        f"{layer}.Depth": [f"{layer}.Depth.Z"],
        f"{layer}.Position": [f"{layer}.Position.{channel}" for channel in ("X", "Y", "Z")],
        f"{layer}.Vector": [f"{layer}.Vector.{channel}" for channel in ("X", "Y", "Z", "W")],
        f"{layer}.Object Index": [f"{layer}.Object Index.X"],
        f"{layer}.Material Index": [f"{layer}.Material Index.X"],
    }


def load_exr(path: Path, width: int, height: int, layer: str, roster: list[str]) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    channels_expected = expected_channels(layer)
    parts, channels, formats, metadata = {}, {}, {}, {}
    names = []
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        image_spec = image.spec()
        name = str(image_spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        names.append(name)
        channels[name] = list(image_spec.channelnames)
        formats[name] = str(image_spec.format)
        metadata[name] = {row.name: json_value(row.value) for row in image_spec.extra_attribs}
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    if names != roster or channels != channels_expected or any(value != "float" for value in formats.values()):
        raise RuntimeError("H2 multipart roster/channels/format mismatch")
    for name in roster:
        expected_shape = (height, width, len(channels_expected[name]))
        if parts[name].shape != expected_shape or not np.isfinite(parts[name]).all():
            raise RuntimeError(f"H2 multipart shape/finite mismatch: {name}")
    return {"parts": parts, "channels": channels, "formats": formats, "metadata": metadata}


def source_identity(report_path: Path, exr_path: Path, spec: dict, repeat: int, frame: int) -> dict:
    report = json.loads(report_path.read_text())
    body = {key: value for key, value in report.items() if key != "reportHash"}
    if report.get("reportHash") != canonical_hash(body):
        raise RuntimeError("H2 source report self-hash mismatch")
    expected = (spec["experimentId"], SPEC_SHA256, CORRECTION_SHA256, spec["fixture"]["id"], repeat, frame, False)
    observed = (report.get("experimentId"), report.get("specSha256"), report.get("correctionSha256"), report.get("fixtureId"), report.get("repeat"), report.get("frame"), report.get("probeOnly"))
    if observed != expected or report.get("output", {}).get("sha256") != sha_file(exr_path):
        raise RuntimeError("H2 source report identity/EXR binding mismatch")
    return report


def write_array(path: Path, value: np.ndarray) -> dict:
    array = np.ascontiguousarray(value, dtype="<f4")
    payload = array.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"uri": str(path), "sha256": sha_bytes(payload), "bytes": len(payload), "shape": list(array.shape), "dtype": "<f4"}


def decoded_records(loaded: dict) -> dict:
    return {
        name: {"sha256": sha_bytes(array.tobytes()), "shape": list(array.shape), "dtype": "<f4"}
        for name, array in loaded["parts"].items()
    }


def main() -> None:
    cli = arguments()
    if sha_file(cli.spec) != SPEC_SHA256 or sha_file(cli.correction) != CORRECTION_SHA256 or cli.output_root.exists() or cli.report.exists():
        raise RuntimeError("H2 adapter identity or output freshness failure")
    spec = json.loads(cli.spec.read_text())
    if cli.fixture != spec["fixture"]["id"]:
        raise RuntimeError("H2 adapter fixture mismatch")
    runtime = spec["runtime"]["python"]
    if sha_file(Path(sys.executable)) != runtime["sha256"] or oiio.VERSION_STRING != runtime["openImageIO"] or np.__version__ != runtime["numpy"]:
        raise RuntimeError("H2 adapter runtime mismatch")
    previous_report = source_identity(cli.previous_report, cli.previous_exr, spec, cli.repeat, 0)
    current_report = source_identity(cli.current_report, cli.current_exr, spec, cli.repeat, 1)
    render = spec["sceneContract"]["render"]
    width, height = render["resolution"]
    layer = render["viewLayer"]
    previous = load_exr(cli.previous_exr, width, height, layer, render["expectedSubimages"])
    current = load_exr(cli.current_exr, width, height, layer, render["expectedSubimages"])
    p, c = previous["parts"], current["parts"]
    decision = {
        "previousRgba": p[f"{layer}.Combined"],
        "currentRgba": c[f"{layer}.Combined"],
        "previousDepth": p[f"{layer}.Depth"][..., 0],
        "currentDepth": c[f"{layer}.Depth"][..., 0],
        "previousOwner": p[f"{layer}.Material Index"][..., 0],
        "currentOwner": c[f"{layer}.Material Index"][..., 0],
        "vector": c[f"{layer}.Vector"][..., :2],
    }
    control = {
        "previousPosition": p[f"{layer}.Position"],
        "currentPosition": c[f"{layer}.Position"],
        "vectorNext": c[f"{layer}.Vector"][..., 2:4],
        "previousObjectIndex": p[f"{layer}.Object Index"][..., 0],
        "currentObjectIndex": c[f"{layer}.Object Index"][..., 0],
    }
    declared_material = {0.0, *(float(owner["materialPassIndex"]) for owner in spec["fixture"]["owners"])}
    declared_object = {0.0, float(spec["fixture"]["owners"][0]["objectPassIndex"])}
    if any(not set(float(v) for v in np.unique(decision[name])).issubset(declared_material) for name in ("previousOwner", "currentOwner")):
        raise RuntimeError("H2 undeclared Material Index")
    if any(not set(float(v) for v in np.unique(control[name])).issubset(declared_object) for name in ("previousObjectIndex", "currentObjectIndex")):
        raise RuntimeError("H2 Object Index negative control mismatch")
    cli.output_root.mkdir(parents=True, exist_ok=False)
    decision_records = {name: write_array(cli.output_root / "decision" / filename, decision[name]) for name, filename in DECISION_FILES.items()}
    control_records = {name: write_array(cli.output_root / "control" / filename, control[name]) for name, filename in CONTROL_FILES.items()}
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerProjectiveDepthAdapter.v0.1",
        "experimentId": spec["experimentId"], "specSha256": SPEC_SHA256, "correctionSha256": CORRECTION_SHA256,
        "fixtureId": cli.fixture, "repeat": cli.repeat, "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha_file(Path(sys.executable)), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "inputs": {
            "previous": {"exrUri": str(cli.previous_exr), "exrSha256": previous_report["output"]["sha256"], "reportUri": str(cli.previous_report), "reportSha256": sha_file(cli.previous_report)},
            "current": {"exrUri": str(cli.current_exr), "exrSha256": current_report["output"]["sha256"], "reportUri": str(cli.current_report), "reportSha256": sha_file(cli.current_report)},
        },
        "multipart": {
            "previousChannels": previous["channels"], "currentChannels": current["channels"],
            "previousFormats": previous["formats"], "currentFormats": current["formats"],
            "previousMetadata": previous["metadata"], "currentMetadata": current["metadata"],
        },
        "decodedPasses": {"previous": decoded_records(previous), "current": decoded_records(current)},
        "decisionDirectory": str(cli.output_root / "decision"), "controlDirectory": str(cli.output_root / "control"),
        "decisionArrays": decision_records, "controlArrays": control_records,
        "operationCounts": {"adapterProcesses": 1, "multipartExrsOpened": 2, "canonicalDecisionArraysWritten": len(decision_records), "canonicalControlArraysWritten": len(control_records), "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
    }
    report = {**body, "reportHash": canonical_hash(body)}
    cli.report.parent.mkdir(parents=True, exist_ok=True)
    cli.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D1214H2_ADAPTER_OK repeat={cli.repeat}")


if __name__ == "__main__":
    main()
