"""Export non-decisional ACES display and adaptive-domain proxies for D12.7."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined(path: Path) -> np.ndarray:
    first = oiio.ImageBuf(str(path), 0, 0)
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if str(image.spec().getattribute("oiio:subimagename") or "").endswith(".Combined"):
            return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)
    raise RuntimeError(f"Combined pass absent: {path}")


def read_mask(path: Path, height: int, width: int) -> np.ndarray:
    values = np.fromfile(path, dtype=np.uint8)
    if values.size != height * width or not set(np.unique(values).tolist()).issubset({0, 1}):
        raise RuntimeError(f"invalid binary mask: {path}")
    return values.reshape(height, width).astype(bool)


def write_png(path: Path, pixels: np.ndarray) -> None:
    encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], encoded.shape[2], oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded):
        raise RuntimeError(writer.geterror())
    writer.close()


def output_record(path: Path) -> dict:
    return {
        "uri": f"public/evidence/b52-d12-7/{path.name}",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def overlay(display: np.ndarray, interior: np.ndarray, boundary: np.ndarray, interior_color: np.ndarray, rejected: np.ndarray | None = None) -> np.ndarray:
    pixels = display * np.float32(0.18)
    pixels[interior] = pixels[interior] * np.float32(0.18) + interior_color * np.float32(0.82)
    pixels[boundary] = pixels[boundary] * np.float32(0.14) + np.asarray([1.0, 0.43, 0.18], dtype=np.float32) * np.float32(0.86)
    if rejected is not None:
        pixels[rejected] = np.asarray([1.0, 0.08, 0.52], dtype=np.float32)
    return np.concatenate((pixels, np.ones((*pixels.shape[:2], 1), dtype=np.float32)), axis=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ocio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    results_path = args.experiment_root / "results.json"
    results = json.loads(results_path.read_text())
    if spec.get("experimentId") != "B52-D12.7" or results.get("experimentId") != "B52-D12.7":
        raise RuntimeError("D12.7 identity mismatch")

    config = ocio.Config.CreateFromFile(str(args.ocio))
    transform = ocio.DisplayViewTransform(
        src="ACEScg",
        display="sRGB - Display",
        view="ACES 2.0 - SDR 100 nits (Rec.709)",
    )
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    names = {
        "STATIC_RIPPLED_BACKDROP_ROUNDED_BOX_117X79": "ripple-rounded-box",
        "STATIC_SUPERELLIPSE_TORUS_139X91": "superellipse-torus",
        "STATIC_FRUSTUM_CROSSBAR_SPHERE_157X103": "frustum-crossbar-sphere",
    }
    measurements = {item["fixtureId"]: item for item in results["measurements"] if item["repeat"] == 1}
    artifacts: list[dict] = []

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        source = args.experiment_root / "sources" / fixture_id / "R1" / "frame-0" / "source.exr"
        beauty = combined(source)
        rgb = beauty[..., :3].reshape(-1, 3)
        display = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32).reshape(height, width, 3)
        alpha = np.clip(beauty[..., 3:4], 0, 1)
        base = names[fixture_id]

        beauty_output = args.output_dir / f"{base}-beauty.png"
        write_png(beauty_output, np.concatenate((display, alpha), axis=2))
        artifacts.append({
            "id": f"{base}-beauty",
            "kind": "ACES_DISPLAY_PROXY",
            "source": {"uri": str(source), "sha256": sha256_file(source)},
            "output": output_record(beauty_output),
        })

        arrays = args.experiment_root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        adaptive_interior_path = arrays / "adaptive-interior.u8"
        adaptive_boundary_path = arrays / "adaptive-boundary.u8"
        adaptive_rejected_path = arrays / "adaptive-rejected.u8"
        radius3_interior_path = arrays / "radius3-interior.u8"
        radius3_boundary_path = arrays / "radius3-boundary.u8"
        adaptive_interior = read_mask(adaptive_interior_path, height, width)
        adaptive_boundary = read_mask(adaptive_boundary_path, height, width)
        adaptive_rejected = read_mask(adaptive_rejected_path, height, width)
        radius3_interior = read_mask(radius3_interior_path, height, width)
        radius3_boundary = read_mask(radius3_boundary_path, height, width)

        adaptive_output = args.output_dir / f"{base}-adaptive.png"
        write_png(adaptive_output, overlay(display, adaptive_interior, adaptive_boundary, np.asarray([0.39, 0.96, 0.55], dtype=np.float32), adaptive_rejected))
        artifacts.append({
            "id": f"{base}-adaptive",
            "kind": "ADAPTIVE_DOMAIN_DIAGNOSTIC",
            "legend": {"green": "adaptive interior", "orange": "owner boundary", "magenta": "risk-rejected radius-2 pixel", "dark": "unregistered"},
            "sources": [
                {"uri": str(path), "sha256": sha256_file(path)}
                for path in (adaptive_interior_path, adaptive_boundary_path, adaptive_rejected_path)
            ],
            "counts": {"interior": int(adaptive_interior.sum()), "boundary": int(adaptive_boundary.sum()), "rejected": int(adaptive_rejected.sum())},
            "output": output_record(adaptive_output),
        })

        radius3_output = args.output_dir / f"{base}-radius3.png"
        write_png(radius3_output, overlay(display, radius3_interior, radius3_boundary, np.asarray([0.29, 0.82, 1.0], dtype=np.float32)))
        artifacts.append({
            "id": f"{base}-radius3",
            "kind": "RADIUS3_COMPARATOR_DOMAIN_DIAGNOSTIC",
            "legend": {"cyan": "radius-3 interior", "orange": "owner boundary", "dark": "unregistered"},
            "sources": [
                {"uri": str(path), "sha256": sha256_file(path)}
                for path in (radius3_interior_path, radius3_boundary_path)
            ],
            "counts": {"interior": int(radius3_interior.sum()), "boundary": int(radius3_boundary.sum())},
            "output": output_record(radius3_output),
        })

        measured = measurements[fixture_id]
        if measured["domains"]["adaptive"]["interiorPixels"] != int(adaptive_interior.sum()) or measured["adaptiveRejectedPixels"] != int(adaptive_rejected.sum()) or measured["domains"]["radius3"]["interiorPixels"] != int(radius3_interior.sum()):
            raise RuntimeError(f"D12.7 diagnostic count mismatch: {fixture_id}")

    manifest = {
        "schemaVersion": "bfs.b52D127SiteProxyManifest.v0.1",
        "decisionRole": "HUMAN_NAVIGATION_ONLY_FORMAL_DECISION_UNCHANGED",
        "experimentId": spec["experimentId"],
        "formalResult": {"uri": str(results_path), "sha256": sha256_file(results_path), "evidenceHash": results["evidenceHash"], "verdict": results["verdict"]},
        "correctedAudit": {"uri": str(args.experiment_root / "audit.c1.json"), "sha256": sha256_file(args.experiment_root / "audit.c1.json")},
        "sourceEncoding": "ACEScg scene-linear float32",
        "display": "sRGB - Display",
        "view": "ACES 2.0 - SDR 100 nits (Rec.709)",
        "ocio": {"uri": str(args.ocio), "sha256": sha256_file(args.ocio), "name": config.getName()},
        "artifacts": artifacts,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D127_SITE_PROXIES_OK count={len(artifacts)} manifest={sha256_file(manifest_path)}")


if __name__ == "__main__":
    main()
