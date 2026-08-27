"""Export non-decisional ACES display and owner-domain proxies for D12.3."""

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


def write_png(path: Path, pixels: np.ndarray) -> None:
    encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], encoded.shape[2], oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded):
        raise RuntimeError(writer.geterror())
    writer.close()


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
    config = ocio.Config.CreateFromFile(str(args.ocio))
    transform = ocio.DisplayViewTransform(
        src="ACEScg",
        display="sRGB - Display",
        view="ACES 2.0 - SDR 100 nits (Rec.709)",
    )
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    names = {
        "STATIC_CURVED_PAIR_97X61": "curved-pair",
        "STATIC_OCCLUDING_PLANES_119X73": "occluding-planes",
        "STATIC_THIN_DEPTH_STACK_131X83": "thin-depth-stack",
    }
    artifacts = []
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        source = args.experiment_root / "sources" / fixture_id / "R1" / "frame-0" / "source.exr"
        beauty = combined(source)
        rgb = beauty[..., :3].reshape(-1, 3)
        display = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32)
        display = display.reshape(height, width, 3)
        alpha = np.clip(beauty[..., 3:4], 0, 1)
        base = names[fixture_id]

        beauty_output = args.output_dir / f"{base}-beauty.png"
        write_png(beauty_output, np.concatenate((display, alpha), axis=2))
        artifacts.append({
            "id": f"{base}-beauty",
            "kind": "ACES_DISPLAY_PROXY",
            "source": {"uri": str(source), "sha256": sha256_file(source)},
            "output": {"uri": str(beauty_output), "sha256": sha256_file(beauty_output), "bytes": beauty_output.stat().st_size},
        })

        consumer = args.experiment_root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        interior = np.fromfile(consumer / "valid.u8", dtype=np.uint8).reshape(height, width).astype(bool)
        boundary = np.fromfile(consumer / "boundary.u8", dtype=np.uint8).reshape(height, width).astype(bool)
        overlay = display * np.float32(0.22)
        overlay[interior] = overlay[interior] * np.float32(0.2) + np.asarray([0.35, 1.0, 0.56], dtype=np.float32) * np.float32(0.8)
        overlay[boundary] = overlay[boundary] * np.float32(0.15) + np.asarray([1.0, 0.46, 0.19], dtype=np.float32) * np.float32(0.85)
        domain_output = args.output_dir / f"{base}-domains.png"
        write_png(domain_output, np.concatenate((overlay, np.ones((height, width, 1), dtype=np.float32)), axis=2))
        artifacts.append({
            "id": f"{base}-domains",
            "kind": "OWNER_INTERIOR_BOUNDARY_DIAGNOSTIC",
            "legend": {"green": "registered owner-interior", "orange": "rejected owner boundary", "dark": "unregistered"},
            "sources": [
                {"uri": str(consumer / "valid.u8"), "sha256": sha256_file(consumer / "valid.u8")},
                {"uri": str(consumer / "boundary.u8"), "sha256": sha256_file(consumer / "boundary.u8")},
            ],
            "counts": {"interior": int(interior.sum()), "boundary": int(boundary.sum())},
            "output": {"uri": str(domain_output), "sha256": sha256_file(domain_output), "bytes": domain_output.stat().st_size},
        })

    manifest = {
        "schemaVersion": "bfs.b52D123SiteProxyManifest.v0.1",
        "decisionRole": "HUMAN_NAVIGATION_ONLY_FORMAL_DECISION_UNCHANGED",
        "experimentId": spec["experimentId"],
        "formalResult": {
            "uri": str(results_path),
            "sha256": sha256_file(results_path),
            "verdict": results["verdict"],
        },
        "sourceEncoding": "ACEScg scene-linear float32",
        "display": "sRGB - Display",
        "view": "ACES 2.0 - SDR 100 nits (Rec.709)",
        "ocio": {"uri": str(args.ocio), "sha256": sha256_file(args.ocio), "name": config.getName()},
        "artifacts": artifacts,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D123_SITE_PROXIES_OK count={len(artifacts)} manifest={sha256_file(manifest_path)}")


if __name__ == "__main__":
    main()
