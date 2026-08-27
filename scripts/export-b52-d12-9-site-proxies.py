"""Export human-navigation overlays for the B52-D12.9-D1 derivation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
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
    if writer is None or not writer.open(str(path), spec) or not writer.write_image(encoded):
        raise RuntimeError(f"cannot write PNG: {path}")
    writer.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--derivation-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-spec", type=Path, required=True)
    parser.add_argument("--ocio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    result_path = args.derivation_root / "results.json"
    result = json.loads(result_path.read_text())
    if result.get("verdict") != "MOTION_AWARE_CURVATURE_RISK_CANDIDATE_DERIVED" or result.get("checkPassed") != result.get("checkTotal"):
        raise RuntimeError("D12.9-D1 derivation is not accepted")
    source_spec = json.loads(args.source_spec.read_text())
    fixture_by_id = {row["id"]: row for row in source_spec["fixtures"]}
    measurements = {row["fixtureId"]: row for row in result["measurements"]}
    names = {
        "RIGID_OBJECT_SWEEP_DISOCCLUSION_149X97": "rigid-sweep-disocclusion",
        "CAMERA_DOLLY_YAW_PARALLAX_BOUNDS_163X101": "camera-parallax-bounds",
        "SAME_INDEX_DEPTH_REVEAL_173X107": "same-index-depth-reveal",
        "MULTI_OWNER_STATIC_CONTROL_127X83": "multi-owner-static-control",
    }
    config = ocio.Config.CreateFromFile(str(args.ocio))
    transform = ocio.DisplayViewTransform(src="ACEScg", display="sRGB - Display", view="ACES 2.0 - SDR 100 nits (Rec.709)")
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    artifacts = []
    for fixture_id in spec["sourceEvidence"]["fixtures"]:
        width, height = fixture_by_id[fixture_id]["resolution"]
        source = args.source_root / "sources" / fixture_id / "R1" / "frame-1" / "source.exr"
        beauty = combined(source)
        display = np.asarray([processor.applyRGB(row.tolist()) for row in beauty[..., :3].reshape(-1, 3)], dtype=np.float32).reshape(height, width, 3)
        old_path = args.source_root / "consumers" / "python" / fixture_id / "R1" / "arrays" / "adaptive-interior.u8"
        new_path = args.derivation_root / "producers" / "python" / fixture_id / "accepted.u8"
        eligible_path = args.derivation_root / "producers" / "python" / fixture_id / "eligible.u8"
        radius_path = args.source_root / "consumers" / "python" / fixture_id / "R1" / "arrays" / "radius2-interior.u8"
        old = np.fromfile(old_path, dtype="u1").reshape(height, width).astype(bool)
        new = np.fromfile(new_path, dtype="u1").reshape(height, width).astype(bool)
        eligible = np.fromfile(eligible_path, dtype="u1").reshape(height, width).astype(bool)
        radius = np.fromfile(radius_path, dtype="u1").reshape(height, width).astype(bool)
        output = display * np.float32(0.10)
        output[radius] = display[radius] * np.float32(0.18) + np.asarray([0.16, 0.38, 0.62], dtype=np.float32) * np.float32(0.52)
        support_rejected = np.logical_and(radius, ~eligible)
        risk_rejected = np.logical_and(eligible, ~new)
        recovered = np.logical_and(new, ~old)
        retained_old = np.logical_and(new, old)
        output[support_rejected] = display[support_rejected] * np.float32(0.08) + np.asarray([1.0, 0.67, 0.10], dtype=np.float32) * np.float32(0.92)
        output[risk_rejected] = display[risk_rejected] * np.float32(0.08) + np.asarray([1.0, 0.07, 0.56], dtype=np.float32) * np.float32(0.92)
        output[recovered] = display[recovered] * np.float32(0.15) + np.asarray([0.14, 0.93, 0.95], dtype=np.float32) * np.float32(0.85)
        output[retained_old] = display[retained_old] * np.float32(0.15) + np.asarray([0.28, 1.0, 0.55], dtype=np.float32) * np.float32(0.85)
        rgba = np.concatenate((output, np.ones((height, width, 1), dtype=np.float32)), axis=2)
        target = args.output_dir / f"{names[fixture_id]}-candidate.png"
        write_png(target, rgba)
        measured = measurements[fixture_id]
        if measured["acceptedPixels"] != int(new.sum()) or measured["oldAdaptivePixels"] != int(old.sum()):
            raise RuntimeError(f"D12.9-D1 proxy count mismatch: {fixture_id}")
        artifacts.append({
            "fixtureId": fixture_id,
            "kind": "D12_9_D1_ACCEPTANCE_COMPARISON",
            "legend": {"cyan": "recovered over D12.8", "green": "accepted by both", "yellow": "support rejected", "magenta": "curvature-risk rejected", "blue": "radius-2 remainder"},
            "counts": {"radius2": int(radius.sum()), "oldAccepted": int(old.sum()), "newAccepted": int(new.sum()), "recovered": int(recovered.sum()), "supportRejected": int(support_rejected.sum()), "riskRejected": int(risk_rejected.sum())},
            "sources": [{"uri": str(path), "sha256": sha_file(path)} for path in (source, old_path, new_path, eligible_path, radius_path)],
            "output": {"uri": f"public/evidence/b52-d12-9-d1/{target.name}", "sha256": sha_file(target), "bytes": target.stat().st_size},
        })
    manifest = {
        "schemaVersion": "bfs.b52D129D1SiteProxyManifest.v0.1",
        "decisionRole": "HUMAN_NAVIGATION_ONLY_DERIVATION_RESULT_UNCHANGED",
        "experimentId": spec["experimentId"],
        "result": {"uri": str(result_path), "sha256": sha_file(result_path), "resultHash": result["resultHash"], "evidenceHash": result["evidenceHash"], "verdict": result["verdict"]},
        "display": "sRGB - Display / ACES 2.0 - SDR 100 nits (Rec.709)",
        "ocio": {"uri": str(args.ocio), "sha256": sha_file(args.ocio)},
        "artifacts": artifacts,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D129_D1_SITE_PROXIES_OK count={len(artifacts)} manifest={sha_file(manifest_path)}")


if __name__ == "__main__":
    main()
