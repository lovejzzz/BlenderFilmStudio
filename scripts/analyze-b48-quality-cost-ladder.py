"""Measure B48-D1 Combined-pass error against the frozen 512-spp reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


AP1_LUMA = np.asarray([0.2722287168, 0.6740817658, 0.0536895174], dtype=np.float64)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_combined(path):
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster = []
    combined = None
    combined_channels = None
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        channels = list(spec.channelnames)
        roster.append({"index": index, "name": name, "channels": channels})
        if name == "Combined" or name.endswith(".Combined"):
            if combined is not None:
                raise RuntimeError(f"multiple Combined subimages: {path}")
            combined = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
            combined_channels = channels
    if combined is None:
        raise RuntimeError(f"Combined subimage absent: {path}")
    if combined.ndim != 3 or combined.shape[2] != 4:
        raise RuntimeError(f"unexpected Combined shape: {combined.shape}")
    if not np.isfinite(combined).all():
        raise RuntimeError(f"non-finite Combined data: {path}")
    metadata = {
        "name": "Combined",
        "shape": list(combined.shape),
        "channels": combined_channels,
        "dtype": "float32-le",
        "order": "C",
    }
    header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return combined, roster, hashlib.sha256(header + combined.tobytes(order="C")).hexdigest()


def exact_top_k_edge_mask(reference_rgb):
    luma = np.maximum(np.tensordot(reference_rgb.astype(np.float64), AP1_LUMA, axes=([2], [0])), 0.0)
    dx = np.zeros_like(luma)
    dy = np.zeros_like(luma)
    dx[:, 1:-1] = 0.5 * (luma[:, 2:] - luma[:, :-2])
    dx[:, 0] = luma[:, 1] - luma[:, 0]
    dx[:, -1] = luma[:, -1] - luma[:, -2]
    dy[1:-1, :] = 0.5 * (luma[2:, :] - luma[:-2, :])
    dy[0, :] = luma[1, :] - luma[0, :]
    dy[-1, :] = luma[-1, :] - luma[-2, :]
    magnitude = np.hypot(dx, dy)
    count = max(1, math.ceil(magnitude.size * 0.10))
    selected = np.argsort(-magnitude.reshape(-1), kind="stable")[:count]
    mask = np.zeros(magnitude.size, dtype=bool)
    mask[selected] = True
    return mask.reshape(magnitude.shape), count, float(magnitude.reshape(-1)[selected[-1]])


def metrics(candidate, reference, edge_mask):
    candidate_rgb = candidate[..., :3].astype(np.float64)
    reference_rgb = reference[..., :3].astype(np.float64)
    delta = candidate_rgb - reference_rgb
    absolute = np.abs(delta)
    rmse = float(np.sqrt(np.mean(np.square(delta))))
    reference_rms = float(np.sqrt(np.mean(np.square(reference_rgb))))
    candidate_luma = np.maximum(np.tensordot(candidate_rgb, AP1_LUMA, axes=([2], [0])), 0.0)
    reference_luma = np.maximum(np.tensordot(reference_rgb, AP1_LUMA, axes=([2], [0])), 0.0)
    log_delta = np.log2(1.0 + candidate_luma) - np.log2(1.0 + reference_luma)
    edge_delta = delta[edge_mask]
    return {
        "linearRmse": rmse,
        "linearNrmseByReferenceRms": rmse / reference_rms if reference_rms else None,
        "linearMae": float(np.mean(absolute)),
        "linearP95AbsoluteError": float(np.percentile(absolute, 95)),
        "linearMaxAbsoluteError": float(np.max(absolute)),
        "logLuminanceRmse": float(np.sqrt(np.mean(np.square(log_delta)))),
        "edgeLinearRmse": float(np.sqrt(np.mean(np.square(edge_delta)))),
        "referenceRms": reference_rms,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.experiment_root / "render.report.json").read_text(encoding="utf-8"))
    observations = []
    arrays = {}
    for cell in report["cells"]:
        path = args.experiment_root / cell["artifact"]["uri"]
        pixels, roster, canonical_hash = read_combined(path)
        arrays[cell["id"]] = pixels
        observations.append(
            {
                "id": cell["id"],
                "samples": cell["samples"],
                "denoising": cell["denoising"],
                "renderSeconds": cell["renderSeconds"],
                "saveSeconds": cell["saveSeconds"],
                "artifact": {"uri": str(path.resolve()), "sha256": sha256_file(path), "bytes": path.stat().st_size},
                "subimageCount": len(roster),
                "subimages": roster,
                "combinedCanonicalFloat32Sha256": canonical_hash,
            }
        )
    reference_id = "S512_REFERENCE"
    reference = arrays[reference_id]
    edge_mask, edge_count, edge_cutoff = exact_top_k_edge_mask(reference[..., :3])
    baseline = next(item for item in observations if item["id"] == "S008_RAW")
    for item in observations:
        item["metricsAgainstReference"] = metrics(arrays[item["id"]], reference, edge_mask)
        item["renderTimeRatioToS008Raw"] = item["renderSeconds"] / baseline["renderSeconds"]
        item["exrByteRatioToS008Raw"] = item["artifact"]["bytes"] / baseline["artifact"]["bytes"]
    result = {
        "schemaVersion": "bfs.qualityCostLadderDerivationAnalysis.v0.1",
        "protocolCommit": report["protocolCommit"],
        "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
        "referenceId": reference_id,
        "edgeMask": {"selection": "stable exact top-k", "fraction": 0.10, "pixelCount": edge_count, "gradientCutoff": edge_cutoff},
        "reportSha256": sha256_file(args.experiment_root / "render.report.json"),
        "observations": observations,
        "nonClaims": [
            "formal production operating point",
            "human preference or cinematic quality",
            "temporal denoiser stability",
            "motion blur, depth of field or 2K/4K behavior",
            "native x86, GPU, cross-host or cloud throughput",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B48_D1_ANALYSIS_OK cells={len(observations)} edgePixels={edge_count}", flush=True)
    for item in observations:
        metric = item["metricsAgainstReference"]
        print(
            f"BFS_B48_D1_METRIC {item['id']} time={item['renderSeconds']:.6f}s "
            f"nrmse={metric['linearNrmseByReferenceRms']:.9f} "
            f"logY={metric['logLuminanceRmse']:.9f} edge={metric['edgeLinearRmse']:.9f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
