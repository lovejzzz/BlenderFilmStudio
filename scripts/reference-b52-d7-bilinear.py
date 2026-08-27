#!/usr/bin/env python3
"""Independent scalar-Python reference worker for B52-D7."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path


SPEC_SHA256 = "f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def arrays(fixture: dict) -> tuple[list[float], list[float]]:
    width, height = fixture["resolution"]
    source = [0.0] * (width * height * 4)
    field = [0.0] * (width * height * 2)
    for y in range(height):
        for x in range(width):
            s = (y * width + x) * 4
            if fixture["sourcePattern"] == "LOW_FREQUENCY_ALPHA_RAMP":
                values = ((x % 64) / 64, (y % 64) / 64, ((x + 3 * y) % 64) / 64, ((x + 2 * y) % 17) / 16)
            elif fixture["sourcePattern"] == "HIGH_FREQUENCY_ALPHA_CHECKER":
                values = ((x ^ y) & 1, ((5 * x + 11 * y) % 16) / 16, ((13 * x + 7 * y) % 32) / 32, ((3 * x + 5 * y) % 9) / 8)
            else:
                raise RuntimeError("unknown source pattern")
            source[s:s + 4] = [f32(value) for value in values]
            d = (y * width + x) * 2
            fixture_id = fixture["id"]
            if fixture_id == "LF_63X47_CLIP_Q1": dx, dy = 1 / 4, 3 / 4
            elif fixture_id == "LF_63X47_EXTEND_MIX": dx, dy = -3 / 2, 1 / 8
            elif fixture_id == "LF_63X47_REPEAT_FIELD": dx, dy = (3 / 8 if x < 31 else -5 / 8), (1 / 4 if y % 2 == 0 else -3 / 4)
            elif fixture_id == "HF_127X73_CLIP_MIX": dx, dy = -3 / 4, 3 / 2
            elif fixture_id == "HF_127X73_EXTEND_MIX": dx, dy = 17 / 8, -3 / 8
            elif fixture_id == "HF_127X73_REPEAT_FIELD": dx, dy = (1 / 8, 5 / 8, -7 / 8, 3 / 8)[x % 4], (-1 / 8, 7 / 8)[y % 2]
            else: raise RuntimeError("unknown fixture")
            field[d:d + 2] = [f32(dx), f32(dy)]
    return source, field


def resolve(value: int, size: int, extension: str) -> int | None:
    if extension == "Clip": return value if 0 <= value < size else None
    if extension == "Extend": return min(max(value, 0), size - 1)
    if extension == "Repeat": return value % size
    raise RuntimeError("unknown extension")


def sample(source: list[float], width: int, height: int, x: int, y: int, ex: str, ey: str) -> tuple[float, float, float, float]:
    sx, sy = resolve(x, width, ex), resolve(y, height, ey)
    if sx is None or sy is None: return 0.0, 0.0, 0.0, 0.0
    index = (sy * width + sx) * 4
    return tuple(source[index:index + 4])


def render(fixture: dict) -> tuple[bytes, str, str]:
    width, height = fixture["resolution"]
    source, field = arrays(fixture)
    output = bytearray(width * height * 16)
    for y in range(height):
        for x in range(width):
            di = (y * width + x) * 2
            u, v = float(x) - float(field[di]), float(y) + float(field[di + 1])
            x0, y0 = math.floor(u), math.floor(v)
            fx, fy = u - x0, v - y0
            weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
            taps = (
                sample(source, width, height, x0, y0, fixture["extensionX"], fixture["extensionY"]),
                sample(source, width, height, x0 + 1, y0, fixture["extensionX"], fixture["extensionY"]),
                sample(source, width, height, x0, y0 + 1, fixture["extensionX"], fixture["extensionY"]),
                sample(source, width, height, x0 + 1, y0 + 1, fixture["extensionX"], fixture["extensionY"]),
            )
            rgba = [f32(taps[0][channel] * weights[0] + taps[1][channel] * weights[1] + taps[2][channel] * weights[2] + taps[3][channel] * weights[3]) for channel in range(4)]
            struct.pack_into("<4f", output, (y * width + x) * 16, *rgba)
    source_bytes = struct.pack(f"<{len(source)}f", *source)
    field_bytes = struct.pack(f"<{len(field)}f", *field)
    return bytes(output), hashlib.sha256(source_bytes).hexdigest(), hashlib.sha256(field_bytes).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    fixture = next((item for item in spec["fixtures"] if item["id"] == args.fixture), None)
    if sha256_file(args.spec) != SPEC_SHA256 or fixture is None: raise RuntimeError("spec or fixture mismatch")
    runtime = spec["runtime"]["pythonReference"]
    if sha256_file(Path(sys.executable)) != runtime["sha256"]: raise RuntimeError("Python runtime mismatch")
    if args.output.exists() or args.report.exists(): raise RuntimeError("refusing to overwrite reference output")
    args.output.parent.mkdir(parents=True, exist_ok=False)
    output, source_hash, field_hash = render(fixture)
    args.output.write_bytes(output)
    body = {"schemaVersion":"bfs.subpixelBilinearPythonReferenceReport.v0.1","experimentId":spec["experimentId"],"fixtureId":args.fixture,"pid":os.getpid(),"runtime":{"executable":sys.executable,"sha256":runtime["sha256"]},"arrays":{"sourceFloat32Sha256":source_hash,"displacementFloat32Sha256":field_hash},"output":{"uri":str(args.output),"sha256":sha256_file(args.output),"bytes":args.output.stat().st_size},"operationCounts":{"pythonReferenceProcesses":1,"nodeReferenceProcesses":0,"blenderProcesses":0,"renderCalls":0}}
    report = {**body, "reportHash": canonical_hash(body)}
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n",encoding="utf-8")
    print(f"BFS_B52_D7_PYTHON_REFERENCE_OK fixture={args.fixture} sha={report['output']['sha256']}")


if __name__ == "__main__": main()
