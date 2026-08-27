#!/usr/bin/env python3
"""Bounded scalar-Python motion quantizer for B52-D11.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path


SPEC_SHA256 = "c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def nearest_integer(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0.0 else math.ceil(value - 0.5)


def quantize(payload: bytes, radius: float) -> tuple[bytes, float]:
    if len(payload) % 4:
        raise RuntimeError("motion payload is not a whole little-endian float32 array")
    values = struct.unpack(f"<{len(payload) // 4}f", payload)
    output: list[float] = []
    maximum_error = 0.0
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise RuntimeError(f"QUANTIZER_DOMAIN nonfinite component={index}")
        candidate = nearest_integer(value)
        error = abs(value - candidate)
        if error > radius:
            raise RuntimeError(
                f"QUANTIZER_DOMAIN component={index} value={value!r} candidate={candidate} error={error!r} radius={radius!r}"
            )
        maximum_error = max(maximum_error, error)
        output.append(0.0 if candidate == 0 else float(candidate))
    encoded = struct.pack(f"<{len(output)}f", *output)
    if quantize_integral(encoded) != encoded:
        raise RuntimeError("quantizer idempotence failure")
    return encoded, maximum_error


def quantize_integral(payload: bytes) -> bytes:
    values = struct.unpack(f"<{len(payload) // 4}f", payload)
    output = [0.0 if value == 0.0 else float(nearest_integer(value)) for value in values]
    return struct.pack(f"<{len(output)}f", *output)


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if sha(args.spec) != SPEC_SHA256 or fixture is None:
        raise RuntimeError("B52-D11.1 spec or fixture identity mismatch")
    if sha(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("Python runtime identity mismatch")
    if args.output.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D11.1 Python quantizer output")

    adapter = json.loads(args.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body):
        raise RuntimeError("adapter report self-hash mismatch")
    if adapter.get("fixtureId") != args.fixture or adapter.get("repeat") != args.repeat:
        raise RuntimeError("adapter report cell mismatch")
    if adapter["arrays"]["motion"]["sha256"] != sha(args.input):
        raise RuntimeError("adapter motion binding mismatch")

    width, height = spec["scene"]["resolution"]
    payload = args.input.read_bytes()
    if len(payload) != width * height * 2 * 4:
        raise RuntimeError("motion input size mismatch")
    radius = float(spec["quantizerContract"]["acceptanceRadiusPixels"])
    encoded, maximum_error = quantize(payload, radius)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    output_record = {
        "uri": str(args.output),
        "sha256": sha(args.output),
        "bytes": args.output.stat().st_size,
        "shape": [height, width, 2],
        "dtype": "little-endian-float32",
    }
    body = {
        "schemaVersion": "bfs.blenderNearestIntegerTemporalRecoveryPythonQuantizerReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "producer": "python",
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha(Path(sys.executable))},
        "adapterReport": {"uri": str(args.adapter_report), "sha256": sha(args.adapter_report)},
        "input": {"uri": str(args.input), "sha256": sha(args.input), "bytes": len(payload)},
        "output": output_record,
        "quantizer": {
            "candidate": "value >= 0 ? floor(value + 0.5) : ceil(value - 0.5)",
            "acceptanceRadiusPixels": radius,
            "wholeArrayAccepted": True,
            "positiveZeroCanonical": True,
            "idempotent": True,
        },
        "metrics": {"componentCount": len(payload) // 4, "maximumAbsoluteQuantizationErrorPixelsDecimal": f"{maximum_error:.18f}"},
        "operationCounts": {"pythonQuantizerProcesses": 1, "nodeQuantizerProcesses": 0, "modelCalls": 0, "networkCalls": 0},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({**body, "reportHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        f"BFS_B52_D11_1_PYTHON_QUANTIZER_OK fixture={args.fixture} repeat={args.repeat} "
        f"components={len(payload) // 4} maxError={maximum_error:.12g} output={output_record['sha256']}"
    )


if __name__ == "__main__":
    main()
