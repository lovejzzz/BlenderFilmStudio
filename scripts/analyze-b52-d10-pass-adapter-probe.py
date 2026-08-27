#!/usr/bin/env python3
"""Analyze non-formal B52-D10 Vector/Depth/IndexOB development sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


EXPECTED_PARTS = {
    "BFS_MASTER.Combined": 4,
    "BFS_MASTER.Depth": 1,
    "BFS_MASTER.Vector": 4,
    "BFS_MASTER.Object Index": 1,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_multipart(path: Path) -> dict:
    first = oiio.ImageBuf(str(path), 0, 0)
    if first.has_error:
        raise RuntimeError(first.geterror())
    roster, parts, channels = [], {}, {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        parts[name] = pixels
        channels[name] = list(spec.channelnames)
    return {"roster": roster, "parts": parts, "channels": channels}


def vector(value: list[float], other: list[float]) -> np.ndarray:
    return np.asarray(value, dtype=np.float64) - np.asarray(other, dtype=np.float64)


def projection_candidates(rows: list[dict], object_name: str) -> dict[str, np.ndarray]:
    by_frame = {row["frame"]: row for row in rows if row["object"] == object_name}
    previous = by_frame[0]["screenPx"]
    current = by_frame[1]["screenPx"]
    following = by_frame[2]["screenPx"]
    return {
        "PREVIOUS_MINUS_CURRENT": vector(previous, current),
        "CURRENT_MINUS_PREVIOUS": vector(current, previous),
        "NEXT_MINUS_CURRENT": vector(following, current),
        "CURRENT_MINUS_NEXT": vector(current, following),
    }


def finite_stats(values: np.ndarray) -> dict:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    return {
        "finite": bool(flat.size and np.isfinite(flat).all()),
        "minimum": float(np.min(flat)),
        "p50": float(np.quantile(flat, 0.5)),
        "p99": float(np.quantile(flat, 0.99)),
        "maximum": float(np.max(flat)),
    }


def analyze_source(directory: Path) -> tuple[dict, list[dict]]:
    report_path = directory / "source.report.json"
    exr_path = directory / "source.exr"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["classification"] != "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE":
        raise RuntimeError("development classification missing")
    if sha256_file(exr_path) != report["output"]["sha256"]:
        raise RuntimeError("development EXR identity mismatch")
    loaded = load_multipart(exr_path)
    for name, components in EXPECTED_PARTS.items():
        if name not in loaded["parts"] or loaded["parts"][name].shape[-1] != components:
            raise RuntimeError(f"missing or malformed pass: {name}")

    depth = loaded["parts"]["BFS_MASTER.Depth"][..., 0].astype(np.float64)
    motion = loaded["parts"]["BFS_MASTER.Vector"].astype(np.float64)
    ownership = loaded["parts"]["BFS_MASTER.Object Index"][..., 0].astype(np.float64)
    object_rows, fit_rows = [], []
    current_projection = {row["object"]: row for row in report["projections"] if row["frame"] == 1}
    for item in report["geometry"]:
        name = item["name"]
        pass_index = int(item["passIndex"])
        mask = ownership == float(pass_index)
        count = int(np.count_nonzero(mask))
        if count == 0:
            raise RuntimeError(f"no visible IndexOB pixels for {name}")
        observed_pairs = {"XY": np.median(motion[mask, :2], axis=0), "ZW": np.median(motion[mask, 2:4], axis=0)}
        candidates = projection_candidates(report["projections"], name)
        fits = {}
        fit_distributions = {}
        for pair_name, observed in observed_pairs.items():
            indices = slice(0, 2) if pair_name == "XY" else slice(2, 4)
            fits[pair_name] = {
                candidate_name: float(np.linalg.norm(observed - expected))
                for candidate_name, expected in candidates.items()
            }
            fit_distributions[pair_name] = {
                candidate_name: finite_stats(np.linalg.norm(motion[mask, indices] - expected, axis=-1))
                for candidate_name, expected in candidates.items()
            }
            for candidate_name, error in fits[pair_name].items():
                fit_rows.append({"fixtureId": report["fixtureId"], "object": name, "pair": pair_name, "candidate": candidate_name, "errorPixels": error})
        expected_depth = float(current_projection[name]["cameraDepth"])
        depth_error = np.abs(depth[mask] - expected_depth)
        object_rows.append({
            "object": name,
            "passIndex": pass_index,
            "visiblePixelCount": count,
            "ownershipExact": bool(np.all(ownership[mask] == pass_index)),
            "depthExpected": expected_depth,
            "depthAbsoluteError": finite_stats(depth_error),
            "vectorMedian": {key: [float(component) for component in value] for key, value in observed_pairs.items()},
            "projectionCandidates": {key: [float(component) for component in value] for key, value in candidates.items()},
            "vectorCandidateEndpointErrors": fits,
            "vectorCandidateEndpointErrorDistributions": fit_distributions,
        })
    return {
        "fixtureId": report["fixtureId"],
        "sourceExrSha256": sha256_file(exr_path),
        "sourceReportSha256": sha256_file(report_path),
        "roster": loaded["roster"],
        "channels": loaded["channels"],
        "allFinite": bool(all(np.isfinite(value).all() for value in loaded["parts"].values())),
        "vectorAbsoluteComponent": finite_stats(np.abs(motion)),
        "vectorPairMagnitude": {
            "XY": finite_stats(np.linalg.norm(motion[..., :2], axis=-1)),
            "ZW": finite_stats(np.linalg.norm(motion[..., 2:4], axis=-1)),
        },
        "objects": object_rows,
    }, fit_rows


def main() -> None:
    args = arguments()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D10 development observation")
    sources, fits = [], []
    for directory in sorted(path for path in args.input_root.iterdir() if path.is_dir()):
        source, source_fits = analyze_source(directory)
        sources.append(source)
        fits.extend(source_fits)
    if len(sources) != 3:
        raise RuntimeError(f"expected three development sources, observed {len(sources)}")

    # Static rows contain no directional information. Aggregate only rows whose
    # expected candidates are separable by the asymmetric fixture motion.
    aggregate = {}
    for pair in ("XY", "ZW"):
        candidate_errors = {}
        for candidate in ("PREVIOUS_MINUS_CURRENT", "CURRENT_MINUS_PREVIOUS", "NEXT_MINUS_CURRENT", "CURRENT_MINUS_NEXT"):
            rows = [row for row in fits if row["pair"] == pair and row["candidate"] == candidate]
            candidate_errors[candidate] = {
                "sumEndpointErrorPixels": float(sum(row["errorPixels"] for row in rows)),
                "maximumEndpointErrorPixels": float(max(row["errorPixels"] for row in rows)),
                "rowCount": len(rows),
            }
        best = min(candidate_errors, key=lambda name: candidate_errors[name]["sumEndpointErrorPixels"])
        aggregate[pair] = {"bestCandidate": best, "candidates": candidate_errors}

    body = {
        "schemaVersion": "bfs.b52D10PassAdapterDevelopmentObservation.v0.1",
        "classification": "EXPLORATORY_NOT_FORMAL_NOT_PROMOTABLE",
        "runtime": {"openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "sources": sources,
        "vectorPairDerivation": aggregate,
        "nonClaims": [
            "This development observation cannot be promoted as holdout evidence.",
            "Candidate selection includes a Blender-derived projection oracle and requires a fresh independent holdout.",
            "Object Index is evaluated only for opaque, single-owner pixels.",
        ],
    }
    observation = {**body, "observationHash": canonical_hash(body)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(observation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(
        "BFS_B52_D10_DEVELOPMENT_OK "
        f"XY={aggregate['XY']['bestCandidate']} ZW={aggregate['ZW']['bestCandidate']} "
        f"observation={sha256_file(args.output)}"
    )


if __name__ == "__main__":
    main()
