#!/usr/bin/env python3
"""Create and evaluate a development-only external Raw EXR passthrough probe."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/external-canonical-warp-bridge-development-smoke-v0-1"
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
WORKER = ROOT / "blender/probe_b52_d8_external_exr_passthrough.py"
OCIO = ROOT / "color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio"


def array_hash(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype="<f4").tobytes()).hexdigest()


def write_exr(path: Path, pixels: np.ndarray) -> None:
    height, width, channels = pixels.shape
    spec = oiio.ImageSpec(width, height, channels, oiio.FLOAT)
    spec.channelnames = ("R", "G", "B", "A")
    spec.attribute("compression", "zip")
    spec.attribute("oiio:ColorSpace", "Raw")
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(oiio.geterror() or "cannot open development EXR")
    if not writer.write_image(np.ascontiguousarray(pixels, dtype=np.float32)):
        raise RuntimeError(writer.geterror() or "cannot write development EXR")
    writer.close()


def read_exr(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(oiio.geterror() or f"cannot read {path}")
    return np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"refusing to overwrite development probe: {OUT}")
    OUT.mkdir(parents=True)
    width, height = 37, 23
    pixels = np.empty((height, width, 4), dtype=np.float32)
    for y in range(height):
        for x in range(width):
            pixels[y, x] = (
                ((17 * x + 11 * y) % 97) / 31.0 - 0.5,
                ((x ^ (3 * y)) % 43) / 9.0,
                ((5 * x + 7 * y) % 29) / 13.0 - 0.25,
                ((3 * x + 5 * y) % 19) / 18.0,
            )
    source = OUT / "external-source.exr"
    rendered = OUT / "blender-passthrough.exr"
    worker_report = OUT / "blender-report.json"
    write_exr(source, pixels)
    decoded_source = read_exr(source)
    if not np.array_equal(decoded_source, pixels):
        raise RuntimeError("development EXR encode/decode is not float32 exact")
    env = {**os.environ, "OCIO": str(OCIO)}
    completed = subprocess.run(
        [
            str(BLENDER), "--background", "--factory-startup", "--disable-autoexec",
            "--python-exit-code", "1", "--python", str(WORKER), "--",
            "--input", str(source), "--output", str(rendered), "--report", str(worker_report),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    (OUT / "blender.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (OUT / "blender.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Blender development probe failed: {completed.returncode}")
    output = read_exr(rendered)
    delta = np.abs(output.astype(np.float64) - pixels.astype(np.float64))
    body = {
        "schemaVersion": "bfs.externalCanonicalWarpBridgeDevelopmentSmoke.v0.1",
        "classification": "DEVELOPMENT_ONLY_NOT_FORMAL_EVIDENCE",
        "resolution": [width, height],
        "runtime": {"openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "input": {"canonicalFloat32Sha256": array_hash(pixels)},
        "sourceExr": {
            "decodedCanonicalFloat32Sha256": array_hash(decoded_source),
            "encodeDecodeExact": bool(np.array_equal(decoded_source, pixels)),
        },
        "blenderOutput": {
            "decodedCanonicalFloat32Sha256": array_hash(output),
            "exact": bool(np.array_equal(output, pixels)),
            "changedScalars": int(np.count_nonzero(output != pixels)),
            "maximumAbsoluteError": float(delta.max()),
        },
        "range": {
            "minimum": float(pixels.min()),
            "maximum": float(pixels.max()),
            "hasNegative": bool(np.any(pixels < 0.0)),
            "hasAboveOne": bool(np.any(pixels > 1.0)),
            "hasNonOpaqueAlpha": bool(np.any(pixels[:, :, 3] != 1.0)),
        },
        "nonClaim": "This development probe is not preregistered formal evidence.",
    }
    (OUT / "observation.json").write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "BFS_B52_D8_DEVELOPMENT_PROBE "
        f"exact={body['blenderOutput']['exact']} changed={body['blenderOutput']['changedScalars']} "
        f"max={body['blenderOutput']['maximumAbsoluteError']}"
    )


if __name__ == "__main__":
    main()
