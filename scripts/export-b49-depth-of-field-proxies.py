"""Export B49-DOF ACES display proxies and per-shot difference heatmaps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined(path):
    first = oiio.ImageBuf(str(path), 0, 0)
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if str(image.spec().getattribute("oiio:subimagename") or "").endswith(".Combined"):
            return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)
    raise RuntimeError(f"Combined absent: {path}")


def write_png(path, pixels):
    encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], encoded.shape[2], oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec): raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded): raise RuntimeError(writer.geterror())
    writer.close()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--experiment-root", type=Path, required=True); parser.add_argument("--ocio", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True); args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    ids = ("T_REF_A", "T_REF_B", "T_REF_C", "T_C128_ON", "T_C128_OFF", "I_REF_A", "I_REF_B", "I_REF_C", "I_C128_ON", "I_C128_OFF")
    sources = {cell: args.experiment_root / cell / "production.exr" for cell in ids}; arrays = {cell: combined(path) for cell, path in sources.items()}
    for prefix in ("T", "I"): arrays[f"{prefix}_REFERENCE_ENSEMBLE"] = np.mean(np.stack([arrays[f"{prefix}_REF_A"], arrays[f"{prefix}_REF_B"], arrays[f"{prefix}_REF_C"]]).astype(np.float64), axis=0).astype(np.float32)
    config = ocio.Config.CreateFromFile(str(args.ocio)); transform = ocio.DisplayViewTransform(src="ACEScg", display="sRGB - Display", view="ACES 2.0 - SDR 100 nits (Rec.709)"); processor = config.getProcessor(transform).getDefaultCPUProcessor(); artifacts = []
    proxy_cells = {"tabletop-off": "T_C128_OFF", "tabletop-on": "T_C128_ON", "tabletop-reference": "T_REFERENCE_ENSEMBLE", "interior-off": "I_C128_OFF", "interior-on": "I_C128_ON", "interior-reference": "I_REFERENCE_ENSEMBLE"}
    for name, cell in proxy_cells.items():
        pixels = arrays[cell]; rgb = pixels[..., :3].reshape(-1, 3); display = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32).reshape(pixels.shape[0], pixels.shape[1], 3); rgba = np.concatenate((display, np.clip(pixels[..., 3:4], 0, 1)), axis=2); output = args.output_dir / f"{name}.png"; write_png(output, rgba)
        prefix = cell[0]; source_list = [sources[f"{prefix}_REF_A"], sources[f"{prefix}_REF_B"], sources[f"{prefix}_REF_C"]] if cell.endswith("REFERENCE_ENSEMBLE") else [sources[cell]]
        artifacts.append({"id": name, "kind": "ACES_DISPLAY_PROXY", "sourceExrs": [{"uri": str(path), "sha256": sha256_file(path)} for path in source_list], "output": {"uri": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size}})
    for label, prefix in (("tabletop", "T"), ("interior", "I")):
        delta = np.max(np.abs(arrays[f"{prefix}_C128_ON"][..., :3].astype(np.float64) - arrays[f"{prefix}_C128_OFF"][..., :3].astype(np.float64)), axis=2); scale = max(float(np.percentile(delta, 99)), np.finfo(np.float64).eps); normalized = np.clip(delta / scale, 0, 1).astype(np.float32); rgb = np.stack((normalized * .88, normalized, normalized * .28), axis=2); rgba = np.concatenate((rgb, np.ones((*normalized.shape, 1), dtype=np.float32)), axis=2); output = args.output_dir / f"{label}-difference.png"; write_png(output, rgba); artifacts.append({"id": f"{label}-difference", "kind": "LINEAR_MAX_RGB_ABSOLUTE_DIFFERENCE_HEATMAP", "scale": {"black": 0, "fullScale": scale, "clamp": "shot-local 99th percentile"}, "statistics": {"maximum": float(np.max(delta)), "p99": float(np.percentile(delta, 99)), "nonzeroPixels": int(np.count_nonzero(delta))}, "output": {"uri": str(output), "sha256": sha256_file(output), "bytes": output.stat().st_size}})
    manifest = {"schemaVersion": "bfs.b49DepthOfFieldProxyManifest.v0.1", "decisionRole": "HUMAN_NAVIGATION_ONLY", "sourceEncoding": "ACEScg scene-linear float32", "display": "sRGB - Display", "view": "ACES 2.0 - SDR 100 nits (Rec.709)", "differenceScales": "SHOT_LOCAL_NOT_CROSS_SHOT_COMPARABLE", "ocio": {"uri": str(args.ocio), "sha256": sha256_file(args.ocio), "name": config.getName()}, "artifacts": artifacts}; (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(f"BFS_B49_DOF_PROXIES_OK count={len(artifacts)}", flush=True)


if __name__ == "__main__": main()
