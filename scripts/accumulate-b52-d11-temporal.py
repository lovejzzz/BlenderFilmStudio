#!/usr/bin/env python3
"""Generic scalar-Python B52-D11 temporal accumulator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path


SPEC_SHA256 = "f1505c42426e8e286ee1584de3df12fb33b7db57518d6d91e1fd93aa3bed5a5f"
INPUTS = {
    "previousRgba": ("previous.rgba32", 4),
    "currentRgba": ("current.rgba32", 4),
    "previousDepth": ("previous-depth.f32", 1),
    "currentDepth": ("current-depth.f32", 1),
    "previousLayer": ("previous-layer.f32", 1),
    "currentLayer": ("current-layer.f32", 1),
    "motion": ("motion.xy32", 2),
}
OUTPUTS = {
    "validity": "validity.u8",
    "reason": "reason.u8",
    "resolvedRgba": "resolved.rgba32",
    "naiveRgba": "naive.rgba32",
    "wrongSignRgba": "wrong-sign.rgba32",
    "roundNearestValidity": "round-nearest-validity.u8",
    "roundNearestRgba": "round-nearest.rgba32",
}
REASONS = {"VALID": 0, "INVALID_BOUNDS": 1, "INVALID_LAYER": 2, "INVALID_DEPTH": 3, "INVALID_ALPHA": 4}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def read_f32(path: Path, count: int) -> list[float]:
    payload = path.read_bytes()
    if len(payload) != count * 4:
        raise RuntimeError(f"unexpected float32 payload size: {path}")
    return list(struct.unpack(f"<{count}f", payload))


def write_f32(path: Path, values: list[float]) -> None:
    path.write_bytes(struct.pack(f"<{len(values)}f", *values))


def nearest_integer(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def accumulate(arrays: dict[str, list[float]], width: int, height: int, integerizer, sign: int = 1, naive: bool = False):
    previous = arrays["previousRgba"]
    current = arrays["currentRgba"]
    previous_depth = arrays["previousDepth"]
    current_depth = arrays["currentDepth"]
    previous_layer = arrays["previousLayer"]
    current_layer = arrays["currentLayer"]
    motion = arrays["motion"]
    resolved = list(current)
    validity = bytearray(width * height)
    reasons = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            index = y * width + x
            dx = integerizer(motion[index * 2])
            dy = integerizer(motion[index * 2 + 1])
            qx, qy = x - sign * dx, y + sign * dy
            if not (0 <= qx < width and 0 <= qy < height):
                reason = "INVALID_BOUNDS"
            else:
                previous_index = qy * width + qx
                if naive:
                    reason = "VALID"
                elif previous_layer[previous_index] != current_layer[index]:
                    reason = "INVALID_LAYER"
                elif abs(previous_depth[previous_index] - current_depth[index]) > max(1.0, current_depth[index]) / 1024.0:
                    reason = "INVALID_DEPTH"
                elif previous[previous_index * 4 + 3] <= 0.0 or current[index * 4 + 3] <= 0.0:
                    reason = "INVALID_ALPHA"
                else:
                    reason = "VALID"
            reasons[index] = REASONS[reason]
            if reason == "VALID":
                validity[index] = 1
                previous_index = qy * width + qx
                for channel in range(4):
                    resolved[index * 4 + channel] = f32(
                        0.5 * current[index * 4 + channel] + 0.5 * previous[previous_index * 4 + channel]
                    )
    return bytes(validity), bytes(reasons), resolved


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--adapter-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    spec = json.loads(args.spec.read_text())
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if sha(args.spec) != SPEC_SHA256 or fixture is None:
        raise RuntimeError("B52-D11 spec or fixture identity mismatch")
    if sha(Path(sys.executable)) != spec["runtime"]["python"]["sha256"]:
        raise RuntimeError("Python runtime identity mismatch")
    if args.output_dir.exists() or args.report.exists():
        raise RuntimeError("refusing to overwrite D11 Python accumulator output")
    adapter = json.loads(args.adapter_report.read_text())
    adapter_body = {key: value for key, value in adapter.items() if key != "reportHash"}
    if adapter.get("reportHash") != canonical_hash(adapter_body) or adapter.get("fixtureId") != args.fixture or adapter.get("repeat") != args.repeat:
        raise RuntimeError("adapter report identity mismatch")
    width, height = spec["scene"]["resolution"]
    arrays, inputs = {}, {}
    for name, (filename, components) in INPUTS.items():
        path = args.input_dir / filename
        if adapter["arrays"][name]["sha256"] != sha(path):
            raise RuntimeError(f"adapter array binding mismatch: {name}")
        arrays[name] = read_f32(path, width * height * components)
        inputs[name] = {"uri": str(path), "sha256": sha(path), "bytes": path.stat().st_size}

    validity, reason, resolved = accumulate(arrays, width, height, int)
    _, _, naive = accumulate(arrays, width, height, int, naive=True)
    _, _, wrong = accumulate(arrays, width, height, int, sign=-1)
    round_validity, _, rounded = accumulate(arrays, width, height, nearest_integer)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    payloads = {
        "validity": validity,
        "reason": reason,
        "resolvedRgba": struct.pack(f"<{len(resolved)}f", *resolved),
        "naiveRgba": struct.pack(f"<{len(naive)}f", *naive),
        "wrongSignRgba": struct.pack(f"<{len(wrong)}f", *wrong),
        "roundNearestValidity": round_validity,
        "roundNearestRgba": struct.pack(f"<{len(rounded)}f", *rounded),
    }
    records = {}
    for name, filename in OUTPUTS.items():
        target = args.output_dir / filename
        target.write_bytes(payloads[name])
        records[name] = {"uri": str(target), "sha256": sha(target), "bytes": target.stat().st_size}
    body = {
        "schemaVersion": "bfs.blenderRealTexturedTemporalPythonAccumulatorReport.v0.1",
        "experimentId": spec["experimentId"],
        "fixtureId": args.fixture,
        "repeat": args.repeat,
        "producer": "python",
        "pid": os.getpid(),
        "runtime": {"python": sys.version.split()[0], "pythonExecutableSha256": sha(Path(sys.executable))},
        "adapterReport": {"uri": str(args.adapter_report), "sha256": sha(args.adapter_report)},
        "inputs": inputs,
        "integerization": "Python int() truncate toward zero",
        "outputs": records,
        "metrics": {
            "validPixels": sum(validity),
            "invalidPixels": len(validity) - sum(validity),
            "roundNearestValidPixels": sum(round_validity),
            "roundNearestChangedValidityPixels": sum(a != b for a, b in zip(validity, round_validity)),
            "roundNearestChangedResolvedScalars": sum(a != b for a, b in zip(resolved, rounded)),
        },
        "operationCounts": {"pythonAccumulatorProcesses": 1, "nodeAccumulatorProcesses": 0, "modelCalls": 0, "networkCalls": 0},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({**body, "reportHash": canonical_hash(body)}, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D11_PYTHON_OK fixture={args.fixture} repeat={args.repeat} valid={sum(validity)}/{len(validity)} resolved={records['resolvedRgba']['sha256']}")


if __name__ == "__main__":
    main()
