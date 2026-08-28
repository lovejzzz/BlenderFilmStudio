#!/usr/bin/env python3
"""Export source-bound B52-D12.14-C2 categorical maps for the research site."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SCALE = 3
TARGETS = (
    "TOP_MISSING_BOTTOM_AVAILABLE",
    "BOTTOM_MISSING_TOP_AVAILABLE",
    "NEITHER_HORIZONTAL_AVAILABLE",
)
COLORS = {
    "empty": np.array([7, 15, 22], dtype=np.uint8),
    "previous": np.array([193, 67, 139], dtype=np.uint8),
    "radius2": np.array([35, 67, 92], dtype=np.uint8),
    "bilinear": np.array([42, 119, 133], dtype=np.uint8),
    "full": np.array([99, 127, 139], dtype=np.uint8),
    "target": np.array([65, 205, 132], dtype=np.uint8),
    "gutter": np.array([15, 27, 36], dtype=np.uint8),
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path, width: int, height: int) -> np.ndarray:
    payload = path.read_bytes()
    if len(payload) != width * height:
        raise RuntimeError(f"D12.14-C2 proxy shape mismatch: {path}")
    return np.frombuffer(payload, dtype=np.uint8).reshape((height, width)).astype(bool)


def write_png(path: Path, pixels: np.ndarray) -> None:
    enlarged = np.repeat(np.repeat(np.ascontiguousarray(pixels, dtype=np.uint8), SCALE, axis=0), SCALE, axis=1)
    spec = oiio.ImageSpec(enlarged.shape[1], enlarged.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(oiio.geterror() or "D12.14-C2 proxy open failed")
    if not writer.write_image(enlarged) or not writer.close():
        raise RuntimeError(oiio.geterror() or "D12.14-C2 proxy write failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite D12.14-C2 site proxies")
    result_path, audit_path = args.root / "results.json", args.root / "audit.json"
    result, audit = json.loads(result_path.read_text()), json.loads(audit_path.read_text())
    if result["verdict"] != "MATERIAL_OWNER_RIGID_DIRECTIONAL_CALIBRATION_CANDIDATES_DERIVED" or audit["passed"] is not True:
        raise RuntimeError("audited derived D12.14-C2 result required")
    selected = {row["target"]: row for row in result["selected"]}
    maximum_width = max(row["resolution"][0] for row in selected.values())
    maximum_height = max(row["resolution"][1] for row in selected.values())
    args.output_dir.mkdir(parents=True)
    sources, counts, panels_previous, panels_current = {}, {}, [], []
    for target in TARGETS:
        row = selected[target]
        width, height = row["resolution"]
        base = args.root / "oracles/python/selected" / target
        paths = {name: base / f"{name}.u8" for name in ("previous-foreground", "current-radius2", "bilinear-support", "full-stencil", "target")}
        masks = {name: load(path, width, height) for name, path in paths.items()}
        previous = np.broadcast_to(COLORS["empty"], (maximum_height, maximum_width, 3)).copy()
        previous[:height, :width][masks["previous-foreground"]] = COLORS["previous"]
        current = np.broadcast_to(COLORS["empty"], (maximum_height, maximum_width, 3)).copy()
        panel = current[:height, :width]
        panel[masks["current-radius2"]] = COLORS["radius2"]
        panel[masks["bilinear-support"]] = COLORS["bilinear"]
        panel[masks["full-stencil"]] = COLORS["full"]
        panel[masks["target"]] = COLORS["target"]
        panels_previous.append(previous)
        panels_current.append(current)
        sources[target] = {name: {"uri": str(path), "sha256": sha_file(path)} for name, path in paths.items()}
        counts[target] = {
            "candidateId": row["candidateId"],
            "resolution": row["resolution"],
            "previousForeground": int(masks["previous-foreground"].sum()),
            "currentRadius2": int(masks["current-radius2"].sum()),
            "bilinearSupport": int(masks["bilinear-support"].sum()),
            "fullStencil": int(masks["full-stencil"].sum()),
            "target": int(masks["target"].sum()),
        }
    vertical_gutter = np.broadcast_to(COLORS["gutter"], (maximum_height, 4, 3)).copy()
    previous_row = np.concatenate((panels_previous[0], vertical_gutter, panels_previous[1], vertical_gutter, panels_previous[2]), axis=1)
    current_row = np.concatenate((panels_current[0], vertical_gutter, panels_current[1], vertical_gutter, panels_current[2]), axis=1)
    horizontal_gutter = np.broadcast_to(COLORS["gutter"], (4, previous_row.shape[1], 3)).copy()
    pixels = np.concatenate((previous_row, horizontal_gutter, current_row), axis=0)
    output = args.output_dir / "rigid-directional-domain-matrix.png"
    write_png(output, pixels)
    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerRigidDirectionalCalibrationSiteProxyManifest.v0.1",
        "classification": "SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE",
        "formalResult": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result["resultHash"]},
        "independentAudit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"]},
        "mapping": {name: value.astype(int).tolist() for name, value in COLORS.items()},
        "panelOrder": {"columns": list(TARGETS), "rows": ["previous-foreground", "current-domain"]},
        "sources": sources, "counts": counts,
        "outputs": [{"uri": str(output), "sha256": sha_file(output), "nearestScale": SCALE, "width": pixels.shape[1] * SCALE, "height": pixels.shape[0] * SCALE}],
        "nonClaims": [
            "The matrix is a categorical nearest-neighbor rendering of committed masks, not a Blender display transform.",
            "Rows use different coordinate roles: the upper row is previous-frame owner raster; the lower row is current-frame classification.",
            "The visualization adds no evidence beyond the bound arrays and cannot substitute for a future rendered holdout.",
        ],
    }
    body["manifestHash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    (args.output_dir / "manifest.json").write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1214C2_SITE_PROXY_OK output={output.name} hash={body['manifestHash']}")


if __name__ == "__main__":
    main()
