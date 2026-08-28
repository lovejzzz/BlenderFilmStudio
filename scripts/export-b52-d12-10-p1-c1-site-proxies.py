#!/usr/bin/env python3
"""Export source-bound categorical/AOV visualizations for the P1-C1 research page."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


WIDTH, HEIGHT = 193, 127
CROP = (31, 11, 145, 110)
SCALE = 4
COLORS = {
    "background": np.array([32, 78, 112], dtype=np.float64),
    "foreground": np.array([242, 126, 66], dtype=np.float64),
    "shared": np.array([92, 104, 116], dtype=np.float64),
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_png(path: Path, pixels: np.ndarray) -> None:
    encoded = np.ascontiguousarray(pixels, dtype=np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec) or not writer.write_image(encoded) or not writer.close():
        raise RuntimeError(oiio.geterror() or "P1-C1 proxy PNG write failed")


def crop_scale(values: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = CROP
    return np.repeat(np.repeat(values[y0:y1, x0:x1], SCALE, axis=0), SCALE, axis=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--array-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite P1-C1 site proxies")
    result = json.loads(args.result.read_text())
    if result["verdict"] != "MATERIAL_INDEX_AND_CUSTOM_AOV_OWNER_TOKENS_VIABLE" or not result["passed"]:
        raise RuntimeError("P1-C1 accepted result required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source = args.array_root / "frame-0/ACES_SDR/R1"
    files = {
        "object-index-shared.png": ("object-index.f32", "object"),
        "material-index-discrete.png": ("material-index.f32", "material"),
        "custom-aov-filtered.png": ("owner-token-aov.f32", "aov"),
    }
    output_rows = []
    for output_name, (input_name, mode) in files.items():
        input_path = source / input_name
        values = np.frombuffer(input_path.read_bytes(), dtype="<f4").reshape(HEIGHT, WIDTH)
        if mode == "object":
            rgb = np.broadcast_to(COLORS["shared"], (HEIGHT, WIDTH, 3)).copy()
        elif mode == "material":
            rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float64)
            rgb[values == 11.0] = COLORS["background"]
            rgb[values == 23.0] = COLORS["foreground"]
        else:
            mix = np.clip((values.astype(np.float64) - 0.25) / 0.5, 0.0, 1.0)[..., None]
            rgb = COLORS["background"] * (1.0 - mix) + COLORS["foreground"] * mix
        output_path = args.output_dir / output_name
        write_png(output_path, np.rint(crop_scale(rgb)))
        output_rows.append({"uri": str(output_path), "sha256": sha_file(output_path), "sourceUri": str(input_path), "sourceSha256": sha_file(input_path), "mode": mode})
    body = {
        "schemaVersion": "bfs.blenderOwnerTokenPassProbeSiteProxyManifest.v0.1",
        "classification": "SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE",
        "result": {"uri": str(args.result), "sha256": sha_file(args.result), "evidenceHash": result["evidenceHash"]},
        "sourceCell": "F0/ACES_SDR/R1",
        "cropExclusive": {"x0": CROP[0], "y0": CROP[1], "x1": CROP[2], "y1": CROP[3]},
        "nearestScale": SCALE,
        "mapping": {"background": COLORS["background"].astype(int).tolist(), "foreground": COLORS["foreground"].astype(int).tolist(), "sharedObjectIndex": COLORS["shared"].astype(int).tolist(), "aovMix": "clamp((value-0.25)/0.5,0,1)"},
        "outputs": output_rows,
        "nonClaims": ["PNG colors are explanatory mappings, not Blender display transforms.", "Nearest-neighbor enlargement preserves source samples but is not evidence beyond the bound float32 arrays."],
    }
    body["manifestHash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    (args.output_dir / "manifest.json").write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1210_P1_C1_SITE_PROXIES outputs={len(output_rows)} hash={body['manifestHash']}")


if __name__ == "__main__":
    main()
