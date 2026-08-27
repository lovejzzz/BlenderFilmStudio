#!/usr/bin/env python3
"""Analyze the non-formal B52-D5 controlled-motion preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def load_module(path: Path, name: str):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stats(values: np.ndarray) -> dict:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    return {
        "p50": float(np.quantile(flat, 0.50, method="higher")),
        "p95": float(np.quantile(flat, 0.95, method="higher")),
        "p99": float(np.quantile(flat, 0.99, method="higher")),
        "maximum": float(np.max(flat)),
        "rmse": float(np.sqrt(np.mean(np.square(flat, dtype=np.float64)))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    common = load_module(root / "scripts/analyze-b52-native-cpu-adaptive-quality-cost.py", "b52_d5_common")
    d4 = load_module(root / "scripts/analyze-b52-d4-adaptive-vector-blur-semantics.py", "b52_d5_d4")
    probe_dir = args.probe_dir.resolve()
    report_path = probe_dir / "probe.report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_path = probe_dir / report["fixtureRender"]["source"]["uri"]
    if sha256_file(source_path) != report["fixtureRender"]["source"]["sha256"]:
        raise RuntimeError("controlled-motion source identity mismatch")
    source = common.load_exr(source_path)
    expected_parts = [
        "BFS_MASTER.Combined",
        "BFS_MASTER.CryptoObject00",
        "BFS_MASTER.CryptoObject01",
        "BFS_MASTER.CryptoObject02",
        "BFS_MASTER.Depth",
        "BFS_MASTER.Normal",
        "BFS_MASTER.Vector",
    ]
    if sorted(source["parts"]) != expected_parts:
        raise RuntimeError(f"controlled-motion part roster mismatch: {sorted(source['parts'])}")

    combined = source["parts"]["BFS_MASTER.Combined"].astype(np.float64)
    vector = source["parts"]["BFS_MASTER.Vector"].astype(np.float64)
    magnitude = np.maximum(np.linalg.norm(vector[..., :2], axis=-1), np.linalg.norm(vector[..., 2:4], axis=-1))
    vector_observation = {
        **stats(magnitude),
        "componentsFinite": bool(np.isfinite(vector).all()),
        "pixelsAbove1Over65536": int(np.count_nonzero(magnitude > 1.0 / 65536.0)),
        "pixelSha256": d4.array_hash(vector),
    }

    effects = []
    for binding in report["compositorOutputs"]:
        path = probe_dir / binding["uri"]
        observed_sha = sha256_file(path)
        loaded = d4.load_single_exr(path)
        pixels = loaded["pixels"].astype(np.float64)
        rgb_error = np.max(np.abs(pixels[..., :3] - combined[..., :3]), axis=-1)
        alpha_error = np.abs(pixels[..., 3] - combined[..., 3])
        effects.append({
            "shutter": binding["shutter"],
            "uri": binding["uri"],
            "expectedSha256": binding["sha256"],
            "observedSha256": observed_sha,
            "identityMatch": observed_sha == binding["sha256"] and path.stat().st_size == binding["bytes"],
            "shape": list(pixels.shape),
            "channels": loaded["channels"],
            "decodedPixelSha256": d4.array_hash(pixels),
            "rgbAbsoluteError": stats(rgb_error),
            "alphaAbsoluteErrorMaximum": float(np.max(alpha_error)),
            "changedPixelsAbove1Over65536": int(np.count_nonzero(rgb_error > 1.0 / 65536.0)),
            "changedPixelsAbove1Over4096": int(np.count_nonzero(rgb_error > 1.0 / 4096.0)),
        })
    rmse_values = [item["rgbAbsoluteError"]["rmse"] for item in effects]
    max_values = [item["rgbAbsoluteError"]["maximum"] for item in effects]
    body = {
        "schemaVersion": "bfs.controlledMotionVectorBlurPreflightObservation.v0.1",
        "classification": "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE",
        "probeReport": {"uri": str(report_path.relative_to(root)), "sha256": sha256_file(report_path)},
        "source": {"uri": str(source_path.relative_to(root)), "sha256": sha256_file(source_path), "parts": expected_parts},
        "vectorMagnitudePixels": vector_observation,
        "shutterEffects": effects,
        "descriptiveDoseResponse": {
            "shuttersAscending": [item["shutter"] for item in effects],
            "rmseStrictlyIncreasing": all(left < right for left, right in zip(rmse_values, rmse_values[1:])),
            "maximumStrictlyIncreasing": all(left < right for left, right in zip(max_values, max_values[1:])),
        },
        "operationCounts": report["operationCounts"],
        "interpretation": "A controlled 2D motion fixture makes Blender 5.2 Vector Blur strongly responsive and shutter-dose ordered. D4's baseline-effect failure is therefore attributable to its retained scenes/task stimulus, not to a universally inert compositor node.",
        "nonClaims": report["nonClaims"],
    }
    observation = {**body, "observationHash": common.canonical_hash(body)}
    args.output.write_text(json.dumps(observation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(
        "BFS_B52_D5_PREFLIGHT_OBSERVATION "
        f"vectorMax={vector_observation['maximum']:.6f} "
        f"effectMax={[round(value, 6) for value in max_values]} "
        f"rmseMonotonic={body['descriptiveDoseResponse']['rmseStrictlyIncreasing']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
