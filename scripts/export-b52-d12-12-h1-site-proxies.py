#!/usr/bin/env python3
"""Export source-bound B52-D12.12-H1 rejection maps for the research site."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SCALE = 3
QUALITY_LIMIT = 3.0517578125e-5
PRIMARY = [
    ("LEFT_OUTER_MISSING_EXPANSION_173X107", "direction-left.u8"),
    ("RIGHT_OUTER_MISSING_EXPANSION_181X109", "direction-right.u8"),
    ("TOP_OUTER_MISSING_EXPANSION_169X113", "direction-top.u8"),
    ("BOTTOM_OUTER_MISSING_EXPANSION_177X115", "direction-bottom.u8"),
]
COLORS = {
    "empty": np.array([8, 17, 24], dtype=np.uint8),
    "radius": np.array([35, 67, 92], dtype=np.uint8),
    "full": np.array([61, 116, 128], dtype=np.uint8),
    "direction": np.array([244, 188, 66], dtype=np.uint8),
    "directionAccepted": np.array([54, 174, 122], dtype=np.uint8),
    "riskRejected": np.array([191, 61, 139], dtype=np.uint8),
    "qualityExceeded": np.array([239, 78, 77], dtype=np.uint8),
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    payload = path.read_bytes()
    expected = int(np.prod(shape)) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise RuntimeError(f"D12.12-H1 proxy shape mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def write_png(path: Path, pixels: np.ndarray) -> None:
    enlarged = np.repeat(np.repeat(np.ascontiguousarray(pixels, dtype=np.uint8), SCALE, axis=0), SCALE, axis=1)
    spec = oiio.ImageSpec(enlarged.shape[1], enlarged.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(oiio.geterror() or "H1 proxy open failed")
    if not writer.write_image(enlarged) or not writer.close():
        raise RuntimeError(oiio.geterror() or "H1 proxy write failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite D12.12-H1 site proxies")
    spec = json.loads(args.spec.read_text())
    result_path, audit_path = args.root / "results.json", args.root / "audit.json"
    result, audit = json.loads(result_path.read_text()), json.loads(audit_path.read_text())
    if result["verdict"] != "MATERIAL_OWNER_ONE_SIDED_CURVATURE_HOLDOUT_REJECTED" or audit["passed"] is not True:
        raise RuntimeError("audited rejected D12.12-H1 result required")
    fixtures = {row["id"]: row for row in spec["fixtures"]}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sources, counts = {}, {}

    panels = []
    maximum_height = max(fixtures[fixture_id]["resolution"][1] for fixture_id, _ in PRIMARY)
    maximum_width = max(fixtures[fixture_id]["resolution"][0] for fixture_id, _ in PRIMARY)
    for fixture_id, direction_file in PRIMARY:
        width, height = fixtures[fixture_id]["resolution"]
        base = args.root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        radius_path, full_path = base / "control/radius2-interior.u8", base / "control/full-stencil.u8"
        direction_path, accepted_path = base / "control" / direction_file, base / "decision/accepted.u8"
        radius = load(radius_path, "u1", (height, width)).astype(bool)
        full = load(full_path, "u1", (height, width)).astype(bool)
        direction = load(direction_path, "u1", (height, width)).astype(bool)
        accepted = load(accepted_path, "u1", (height, width)).astype(bool)
        pixels = np.broadcast_to(COLORS["empty"], (maximum_height, maximum_width, 3)).copy()
        panel = pixels[:height, :width]
        panel[radius] = COLORS["radius"]
        panel[full] = COLORS["full"]
        panel[direction] = COLORS["direction"]
        panel[direction & accepted] = COLORS["directionAccepted"]
        panels.append(pixels)
        sources[fixture_id] = [str(path) for path in (radius_path, full_path, direction_path, accepted_path)]
        counts[fixture_id] = {"radius2": int(radius.sum()), "fullStencil": int(full.sum()), "directional": int(direction.sum()), "directionalAccepted": int((direction & accepted).sum())}
    gutter = np.broadcast_to(COLORS["empty"], (maximum_height, 4, 3)).copy()
    row_one = np.concatenate((panels[0], gutter, panels[1]), axis=1)
    row_two = np.concatenate((panels[2], gutter, panels[3]), axis=1)
    horizontal = np.broadcast_to(COLORS["empty"], (4, row_one.shape[1], 3)).copy()
    direction_pixels = np.concatenate((row_one, horizontal, row_two), axis=0)
    direction_target = args.output_dir / "directional-witness-matrix.png"
    write_png(direction_target, direction_pixels)

    fixture_id = "NEITHER_HORIZONTAL_STRIP_185X117"
    width, height = fixtures[fixture_id]["resolution"]
    adapter = args.root / "adapters" / fixture_id / "R1" / "arrays"
    consumer = args.root / "consumers" / "python" / fixture_id / "R1" / "arrays"
    paths = {
        "current": adapter / "current.rgba32",
        "reconstructed": consumer / "decision/reconstructed.rgba32",
        "radius": consumer / "control/radius2-interior.u8",
        "right": consumer / "control/direction-right.u8",
        "accepted": consumer / "decision/accepted.u8",
    }
    current = load(paths["current"], "<f4", (height, width, 4))
    reconstructed = load(paths["reconstructed"], "<f4", (height, width, 4))
    radius = load(paths["radius"], "u1", (height, width)).astype(bool)
    right = load(paths["right"], "u1", (height, width)).astype(bool)
    accepted = load(paths["accepted"], "u1", (height, width)).astype(bool)
    exceeded = accepted & np.any(np.abs(reconstructed[..., :3].astype(np.float64) - current[..., :3].astype(np.float64)) > QUALITY_LIMIT, axis=2)
    pixels = np.broadcast_to(COLORS["empty"], (height, width, 3)).copy()
    pixels[radius] = COLORS["radius"]
    pixels[radius & ~accepted] = COLORS["riskRejected"]
    pixels[right] = COLORS["direction"]
    pixels[accepted] = COLORS["directionAccepted"]
    pixels[exceeded] = COLORS["qualityExceeded"]
    quality_target = args.output_dir / "quality-threshold-counterexample.png"
    write_png(quality_target, pixels)
    sources[fixture_id] = [str(path) for path in paths.values()]
    counts[fixture_id] = {"radius2": int(radius.sum()), "rightMissing": int(right.sum()), "accepted": int(accepted.sum()), "riskRejected": int((radius & ~accepted).sum()), "qualityExceededPixels": int(exceeded.sum())}

    outputs = []
    for target in (direction_target, quality_target):
        outputs.append({"uri": str(target), "sha256": sha_file(target), "nearestScale": SCALE})
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureHoldoutSiteProxyManifest.v0.1",
        "classification": "SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE",
        "formalResult": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result["resultHash"]},
        "independentAudit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]},
        "mapping": {name: value.astype(int).tolist() for name, value in COLORS.items()},
        "sources": sources, "counts": counts, "outputs": outputs,
        "nonClaims": [
            "The maps are explanatory categorical encodings of committed arrays, not Blender display transforms.",
            "Nearest-neighbor enlargement adds no evidence beyond the bound source payloads.",
            "The maps do not repair failed fixtures or change the preregistered verdict.",
        ],
    }
    body["manifestHash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    (args.output_dir / "manifest.json").write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1212H1_SITE_PROXIES outputs=2 hash={body['manifestHash']}")


if __name__ == "__main__":
    main()
